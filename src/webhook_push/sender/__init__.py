"""Message sender for webhook-push skill.

This module implements the main message sending logic with retry support,
rate limiting, and automatic platform selection.
"""

from __future__ import annotations

import asyncio
import time
import urllib.parse
from dataclasses import dataclass
from typing import Any, Optional, Union, cast

import httpx

from webhook_push.adapters import AdapterRegistry, PlatformAdapter, default_registry
from webhook_push.models import (
    AutoSendResult,
    MessageContent,
    MultiSendResult,
    PlatformConfig,
    PlatformError,
    PlatformPayload,
    PlatformResponse,
    RetryPolicy,
    SendResult,
    UnifiedMessage,
)


@dataclass
class SenderOptions:
    """Options for message sender."""

    retry_policy: Optional[RetryPolicy] = None
    timeout: int = 5000
    http_client: Optional[httpx.AsyncClient] = None
    registry: Optional[AdapterRegistry] = None


class MessageSender:
    """Main interface for sending messages.

    This class provides a unified interface for sending messages to one or
    multiple platforms, with built-in retry logic and rate limiting.
    """

    def __init__(self, options: Optional[SenderOptions] = None):
        """Initialize the message sender.

        Args:
            options: Sender options (optional)
        """
        self._options = options or SenderOptions()
        self._registry = self._options.registry or default_registry
        self._http_client = self._options.http_client
        self._retry_policy = self._options.retry_policy or RetryPolicy()

    async def send(
        self,
        message: UnifiedMessage,
        platform: str,
        webhook_url: Optional[str] = None
    ) -> SendResult:
        """Send a message to a specific platform.

        Args:
            message: The message to send
            platform: Target platform name
            webhook_url: Optional webhook URL override

        Returns:
            SendResult indicating success or failure
        """
        adapter = self._registry.get(platform)

        if not adapter:
            return SendResult(
                success=False,
                error=PlatformError(
                    code="UNKNOWN_PLATFORM",
                    message=f"Unknown platform: {platform}"
                )
            )

        # Get a consistent timestamp for signature calculation
        # This ensures the same timestamp is used for both signature and sending
        current_timestamp = int(time.time())
        if hasattr(adapter, '_timestamp_override'):
            adapter._timestamp_override = current_timestamp

        # Use provided webhook URL if given
        if webhook_url:
            # Create a temporary adapter with the URL
            new_adapter = self._create_adapter_with_url(platform, webhook_url)
            # If the original adapter has a secret, copy it to the new adapter
            if hasattr(adapter, '_secret') and adapter._secret and hasattr(new_adapter, '_secret'):
                new_adapter._secret = adapter._secret
            # Set consistent timestamp for signature
            if hasattr(new_adapter, '_timestamp_override'):
                new_adapter._timestamp_override = current_timestamp
            adapter = new_adapter

        # Check support level
        support_level = adapter.supports(message)

        if support_level == "none":
            # Try to downgrade the message
            downgraded = self._downgrade_message(message)
            if downgraded:
                return await self.send(downgraded, platform, webhook_url)

            return SendResult(
                success=False,
                error=PlatformError(
                    code="UNSUPPORTED",
                    message=f"Platform {platform} does not support this message type"
                )
            )

        # Transform message to platform format
        payload = adapter.transform(message)

        # Check rate limit
        rate_limit = adapter.get_rate_limit_info()
        if rate_limit.remaining <= 0:
            return SendResult(
                success=False,
                error=PlatformError(
                    code="RATE_LIMIT",
                    message="Rate limit exceeded"
                ),
                retry_suggested=True
            )

        # Send with retry
        return await self._send_with_retry(adapter, payload)

    async def send_multi(
        self,
        message: UnifiedMessage,
        platforms: list[str],
        webhook_urls: Optional[dict[str, str]] = None
    ) -> MultiSendResult:
        """Send a message to multiple platforms.

        Args:
            message: The message to send
            platforms: List of platform names
            webhook_urls: Optional webhook URL overrides per platform

        Returns:
            MultiSendResult with results for each platform
        """
        urls = webhook_urls or {}

        tasks = [
            self.send(message, platform, urls.get(platform))
            for platform in platforms
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = 0
        failed_count = 0
        result_details = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_obj = PlatformError(code="EXCEPTION", message=str(result))
                result_details.append({
                    "platform": platforms[i],
                    "success": False,
                    "error": error_obj.model_dump()
                })
                failed_count += 1
            elif cast(SendResult, result).success:
                success_count += 1
                result_details.append({
                    "platform": platforms[i],
                    "success": True,
                    "message_id": cast(SendResult, result).message_id
                })
            else:
                failed_count += 1
                send_result = cast(SendResult, result)
                error_dict = send_result.error.model_dump() if send_result.error else None
                result_details.append({
                    "platform": platforms[i],
                    "success": False,
                    "error": error_dict
                })

        return MultiSendResult(
            total=len(platforms),
            success_count=success_count,
            failed_count=failed_count,
            results=result_details
        )

    async def send_auto(
        self,
        message: UnifiedMessage
    ) -> AutoSendResult:
        """Send a message to all available platforms.

        Args:
            message: The message to send

        Returns:
            AutoSendResult with results for each platform
        """
        available_adapters = self._registry.can_send(message)

        results: dict[str, SendResult] = {}
        sent_platforms: list[str] = []
        skipped_platforms: list[str] = []

        for adapter in available_adapters:
            result = await self.send(message, adapter.platform)

            results[adapter.platform] = result

            if result.success or result.retry_suggested:
                sent_platforms.append(adapter.platform)
            else:
                skipped_platforms.append(adapter.platform)

        return AutoSendResult(
            sent_platforms=sent_platforms,
            skipped_platforms=skipped_platforms,
            results=results
        )

    async def _send_with_retry(
        self,
        adapter: PlatformAdapter,
        payload: PlatformPayload
    ) -> SendResult:
        """Send a message with retry logic.

        Args:
            adapter: Platform adapter
            payload: Platform-specific payload

        Returns:
            SendResult from the final attempt
        """
        last_result: Optional[SendResult] = None

        for attempt in range(self._retry_policy.max_retries + 1):
            try:
                response = await self._http_post(
                    adapter.get_webhook_url(),
                    payload.body,
                    payload.headers,
                    payload.query
                )

                result = adapter.parse_response(response)

                if result.success:
                    return result

                # Check if we should retry
                if result.retry_suggested and attempt < self._retry_policy.max_retries:
                    delay = self._get_backoff_delay(attempt)
                    await asyncio.sleep(delay / 1000)
                    continue

                return result

            except Exception as error:
                if attempt < self._retry_policy.max_retries:
                    delay = self._get_backoff_delay(attempt)
                    await asyncio.sleep(delay / 1000)
                    last_result = SendResult(
                        success=False,
                        error=PlatformError(
                            code="NETWORK_ERROR",
                            message=str(error)
                        ),
                        retry_suggested=True
                    )
                else:
                    return SendResult(
                        success=False,
                        error=PlatformError(
                            code="NETWORK_ERROR",
                            message=str(error)
                        )
                    )

        return last_result or SendResult(
            success=False,
            error=PlatformError(code="UNKNOWN", message="Unknown error")
        )

    async def _http_post(
        self,
        url: str,
        data: dict[str, Any],
        headers: Optional[dict[str, str]] = None,
        query: Optional[dict[str, str]] = None
    ) -> PlatformResponse:
        """Make an HTTP POST request.

        Args:
            url: Target URL
            data: Request body data
            headers: Optional request headers
            query: Optional query parameters

        Returns:
            PlatformResponse with the response
        """
        client = self._http_client or httpx.AsyncClient(timeout=self._options.timeout)

        request_headers = dict(headers) if headers else {}
        request_headers["Content-Type"] = "application/json"

        # Build URL with query parameters if provided
        if query:
            url_parts = list(urllib.parse.urlparse(url))
            query_params = dict(urllib.parse.parse_qsl(url_parts[4]))
            query_params.update(query)
            url_parts[4] = urllib.parse.urlencode(query_params)
            url = urllib.parse.urlunparse(url_parts)

        try:
            # If data is already a string (pre-serialized JSON), send as content
            if isinstance(data, str):
                response = await client.post(
                    url,
                    content=data,
                    headers={**request_headers, "Content-Type": "application/json"}
                )
            else:
                response = await client.post(
                    url,
                    json=data,
                    headers=request_headers
                )

            response_data = response.json()
            # For Feishu, check if the response contains an error code
            if response.status_code == 200 and isinstance(response_data, dict) and response_data.get('code') != 0:
                # Feishu returns 200 but with error code in body
                return PlatformResponse(
                    status_code=response_data.get('code', response.status_code),
                    body=response_data,
                    headers=dict(response.headers)
                )

            return PlatformResponse(
                status_code=response.status_code,
                body=response_data,
                headers=dict(response.headers)
            )
        finally:
            if not self._http_client:
                await client.aclose()

    def _get_backoff_delay(self, attempt: int) -> int:
        """Calculate backoff delay for retry.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in milliseconds
        """
        delay = self._retry_policy.initial_delay * (
            self._retry_policy.backoff_multiplier ** attempt
        )
        return int(min(delay, self._retry_policy.max_delay))

    def _downgrade_message(self, message: UnifiedMessage) -> Optional[UnifiedMessage]:
        """Downgrade a message to a simpler format.

        Args:
            message: The original message

        Returns:
            Downgraded message or None if downgrade not possible
        """
        from webhook_push.converters import CardConverter, MarkdownConverter

        msg_type = message.content.type

        if msg_type == "card":
            # Try to downgrade card to markdown
            card_body = message.content.body
            downgraded = CardConverter.downgrade(card_body)

            return UnifiedMessage(
                metadata=message.metadata,
                content=MessageContent(
                    type="markdown",
                    body=downgraded.get("body", {})
                )
            )

        if msg_type == "markdown":
            # Downgrade markdown to text
            body = message.content.body
            text = MarkdownConverter.downgrade(body.get("content", ""))

            return UnifiedMessage(
                metadata=message.metadata,
                content=MessageContent(
                    type="text",
                    body={"text": text}
                )
            )

        return None

    def _create_adapter_with_url(
        self,
        platform: str,
        webhook_url: str
    ) -> PlatformAdapter:
        """Create a temporary adapter with a specific webhook URL.

        Args:
            platform: Platform name
            webhook_url: Webhook URL

        Returns:
            PlatformAdapter instance
        """
        from webhook_push.adapters import DingTalkAdapter, FeishuAdapter, WeComAdapter

        if platform == "wecom":
            # Extract key from URL
            key = webhook_url.split("key=")[-1] if "key=" in webhook_url else ""
            return WeComAdapter(key)

        elif platform == "dingtalk":
            # Extract token from URL
            token = webhook_url.split("access_token=")[-1] if "access_token=" in webhook_url else ""
            return DingTalkAdapter(token)

        elif platform == "feishu":
            # Extract ID from URL
            webhook_id = webhook_url.split("/hook/")[-1].split("?")[0]
            return FeishuAdapter(webhook_id)

        raise ValueError(f"Unknown platform: {platform}")

    def _create_adapter_from_config(
        self,
        platform: str,
        config: PlatformConfig
    ) -> PlatformAdapter:
        """Create an adapter from platform configuration.

        Args:
            platform: Platform name
            config: Platform configuration with webhook_url and optional secret

        Returns:
            PlatformAdapter instance
        """
        from webhook_push.adapters import DingTalkAdapter, FeishuAdapter, WeComAdapter

        if platform == "wecom":
            # Extract key from URL
            key = config.webhook_url.split("key=")[-1] if "key=" in config.webhook_url else ""
            return WeComAdapter(webhook_key=key)

        elif platform == "dingtalk":
            # Extract token from URL
            token = config.webhook_url.split("access_token=")[-1] if "access_token=" in config.webhook_url else ""
            return DingTalkAdapter(access_token=token, secret=config.secret)

        elif platform == "feishu":
            # Extract ID from URL
            webhook_id = config.webhook_url.split("/hook/")[-1].split("?")[0]
            return FeishuAdapter(webhook_id=webhook_id, secret=config.secret)

        raise ValueError(f"Unknown platform: {platform}")


class SyncMessageSender:
    """Synchronous wrapper for MessageSender.

    This class provides a synchronous interface for sending messages,
    useful for non-async contexts.
    """

    def __init__(self, options: Optional[SenderOptions] = None):
        self._sender = MessageSender(options)

    def send(
        self,
        message: UnifiedMessage,
        platform: str,
        webhook_url: Optional[str] = None
    ) -> SendResult:
        """Send a message synchronously."""
        return asyncio.run(self._sender.send(message, platform, webhook_url))

    def send_multi(
        self,
        message: UnifiedMessage,
        platforms: list[str],
        webhook_urls: Optional[dict[str, str]] = None
    ) -> MultiSendResult:
        """Send to multiple platforms synchronously."""
        return asyncio.run(self._sender.send_multi(message, platforms, webhook_urls))

    def send_auto(self, message: UnifiedMessage) -> AutoSendResult:
        """Auto-send synchronously."""
        return asyncio.run(self._sender.send_auto(message))
