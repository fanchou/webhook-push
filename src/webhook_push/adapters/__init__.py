"""Platform adapters for webhook-push skill.

This module implements platform-specific adapters for WeCom, DingTalk, and Feishu.
Each adapter handles the translation between the unified message model and
platform-specific APIs.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
from abc import ABC, abstractmethod
from typing import Any, Optional, cast

from webhook_push.models import (
    CardType,
    MessageType,
    PlatformError,
    PlatformPayload,
    PlatformResponse,
    RateLimitInfo,
    SendResult,
    SupportLevel,
    UnifiedMessage,
)

# Rate limit error code constants
WECOM_RATE_LIMIT_CODE = 60008
DINGTALK_RATE_LIMIT_CODE = 60008


# ============================================================================
# Base Adapter
# =========================================================================


class PlatformAdapter(ABC):
    """Abstract base class for platform adapters."""

    @property
    @abstractmethod
    def platform(self) -> str:
        """Platform identifier."""

    @property
    @abstractmethod
    def priority(self) -> int:
        """Adapter priority (lower = higher priority)."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the adapter is available."""

    @abstractmethod
    def supports(self, message: UnifiedMessage) -> SupportLevel:
        """Check if the adapter supports the message type."""

    @abstractmethod
    def transform(self, message: UnifiedMessage) -> PlatformPayload:
        """Transform unified message to platform-specific format."""

    @abstractmethod
    def parse_response(self, response: PlatformResponse) -> SendResult:
        """Parse platform response to unified result."""

    @abstractmethod
    def get_rate_limit_info(self) -> RateLimitInfo:
        """Get rate limit information."""

    @abstractmethod
    def get_webhook_url(self) -> str:
        """Get the webhook URL."""


# ============================================================================
# Enterprise WeCom Adapter
# =========================================================================


class WeComAdapter(PlatformAdapter):
    """Adapter for Enterprise WeChat (企业微信)."""

    @property
    def platform(self) -> str:
        return "wecom"

    @property
    def priority(self) -> int:
        return 1

    def __init__(self, webhook_key: str):
        self._webhook_key = webhook_key
        self._rate_limit_remaining = 20

    def is_available(self) -> bool:
        return bool(self._webhook_key)

    def supports(self, message: UnifiedMessage) -> SupportLevel:
        msg_type = message.content.type

        fully_supported = [
            MessageType.TEXT,
            MessageType.MARKDOWN,
            MessageType.IMAGE,
            "news",  # news type
            MessageType.FILE,
            "voice",  # voice type
        ]
        partially_supported = [MessageType.CARD]

        if msg_type in fully_supported:
            return cast(SupportLevel, SupportLevel.FULL)
        elif msg_type in partially_supported:
            return cast(SupportLevel, SupportLevel.PARTIAL)
        return cast(SupportLevel, SupportLevel.NONE)

    def transform(self, message: UnifiedMessage) -> PlatformPayload:
        body: dict[str, Any] = {"msgtype": message.content.type}
        warnings: list[str] = []

        msg_type = message.content.type
        body_content = message.content.body

        if msg_type == MessageType.TEXT:
            body["text"] = {
                "content": body_content.get("text", "")
            }
            # Handle mentions
            if message.content.mentions:
                mentioned_list = []
                mentioned_mobile_list = []
                for mention in message.content.mentions:
                    if mention.type == "all":
                        mentioned_list.append("@all")
                        mentioned_mobile_list.append("@all")
                    elif mention.type == "user_id":
                        mentioned_list.append(mention.value)
                    elif mention.type == "mobile":
                        mentioned_mobile_list.append(mention.value)
                body["text"]["mentioned_list"] = mentioned_list
                body["text"]["mentioned_mobile_list"] = mentioned_mobile_list

        elif msg_type == MessageType.MARKDOWN:
            content = body_content.get("content", "")

            # Auto-detect if content contains tables (markdown_v2 feature)
            # WeCom standard markdown doesn't support tables
            has_table = "|" in content and content.count("|") >= 2

            enhanced = body_content.get("enhanced", False) or has_table

            body["msgtype"] = "markdown_v2" if enhanced else "markdown"
            body["markdown_v2" if enhanced else "markdown"] = {
                "content": content
            }

            if has_table and not enhanced:
                warnings.append("Tables require markdown_v2, auto-upgraded")

        elif msg_type == MessageType.IMAGE:
            body["image"] = {
                "base64": body_content.get("base64", ""),
                "md5": body_content.get("md5", "")
            }

        elif msg_type == "news":
            body["news"] = {
                "articles": [
                    {
                        "title": link.get("title", ""),
                        "description": link.get("title", ""),
                        "url": link.get("url", ""),
                        "picurl": link.get("image_url", "")
                    }
                    for link in body_content.get("links", [])
                ]
            }

        elif msg_type == MessageType.CARD:
            # WeCom uses "template_card" instead of "card"
            body["msgtype"] = "template_card"
            body["template_card"] = self._transform_card(body_content)

        return PlatformPayload(body=body, warnings=warnings)

    def _transform_card(self, card_body: dict[str, Any]) -> dict[str, Any]:
        """Transform card to WeCom template_card format."""
        from webhook_push.models import (
            WeComCardAction,
            WeComEmphasisContent,
            WeComHorizontalContent,
            WeComJumpList,
            WeComQuoteArea,
            WeComSource,
        )

        card_type = card_body.get("card_type", "text_notice")

        result: dict[str, Any] = {
            "card_type": card_type
        }

        # Source info
        if "source" in card_body:
            source_data = card_body["source"]
            result["source"] = WeComSource(
                icon_url=source_data.get("icon_url"),
                desc=source_data.get("desc"),
                desc_color=source_data.get("desc_color")
            ).model_dump(exclude_none=True)

        # Main title
        if "main_title" in card_body or card_body.get("title"):
            main_title_data = card_body.get("main_title", {})
            result["main_title"] = {
                "title": main_title_data.get("title", "") or card_body.get("title", ""),
                "desc": main_title_data.get("desc") or card_body.get("description", "")
            }

        # Emphasis content
        if "emphasis" in card_body or "emphasis_content" in card_body:
            emph = card_body.get("emphasis") or card_body.get("emphasis_content", {})
            result["emphasis_content"] = WeComEmphasisContent(
                title=emph.get("title", ""),
                desc=emph.get("desc")
            ).model_dump(exclude_none=True)

        # Quote area
        if "quote" in card_body or "quote_area" in card_body:
            quote = card_body.get("quote") or card_body.get("quote_area", {})
            result["quote_area"] = WeComQuoteArea(
                type=quote.get("type", 1),
                url=quote.get("url"),
                appid=quote.get("appid"),
                pagepath=quote.get("pagepath"),
                title=quote.get("title"),
                quote_text=quote.get("quote_text")
            ).model_dump(exclude_none=True)

        # Sub title text
        if "sub_title" in card_body or "sub_title_text" in card_body:
            result["sub_title_text"] = (
                card_body.get("sub_title") or card_body.get("sub_title_text", "")
            )

        # Horizontal content list
        if "horizontal" in card_body or "horizontal_content_list" in card_body:
            horiz_list = card_body.get("horizontal") or card_body.get("horizontal_content_list", [])
            result["horizontal_content_list"] = [
                WeComHorizontalContent(
                    keyname=item.get("keyname", item.get("key", "")),
                    value=item.get("value", ""),
                    type=item.get("type"),
                    url=item.get("url"),
                    media_id=item.get("media_id")
                ).model_dump(exclude_none=True)
                for item in horiz_list
            ]

        # Jump list
        if "jumps" in card_body or "jump_list" in card_body:
            jump_list = card_body.get("jumps") or card_body.get("jump_list", [])
            result["jump_list"] = [
                WeComJumpList(
                    type=item.get("type", 1),
                    url=item.get("url"),
                    title=item.get("title")
                ).model_dump(exclude_none=True)
                for item in jump_list
            ]

        # Card action
        if "action" in card_body or "card_action" in card_body:
            action = card_body.get("action") or card_body.get("card_action", {})
            result["card_action"] = WeComCardAction(
                type=action.get("type", 1),
                url=action.get("url")
            ).model_dump(exclude_none=True)

        # Handle text_notice specific: single button
        if card_type == "text_notice":
            actions = card_body.get("actions", [])
            if actions:
                action = actions[0]
                result["singleTitle"] = action.get("text", "")
                result["singleURL"] = action.get("url", "")

        # Handle news_show specific: image and URL
        if card_type == "news_show":
            # news_show requires: card_image, title, url
            if card_body.get("image_url") or card_body.get("card_image"):
                result["card_image"] = card_body.get("image_url") or card_body.get("card_image")

            # Get title from main_title.title or top-level title
            title = None
            if "main_title" in card_body and "title" in card_body["main_title"]:
                title = card_body["main_title"]["title"]
            elif card_body.get("title"):
                title = card_body.get("title")
            elif "title" in card_body:
                title = card_body["title"]

            if title:
                result["title"] = title

            if card_body.get("url"):
                result["url"] = card_body.get("url")

        # Legacy support: extract text from elements
        elements = card_body.get("elements", [])
        if "text" not in result and elements:
            text_parts = []
            for elem in elements:
                if elem.get("text"):
                    text_parts.append(elem["text"])
            if text_parts:
                result["text"] = "\n".join(text_parts)

        return result

    def parse_response(self, response: PlatformResponse) -> SendResult:
        body = response.body

        if body.get("errcode") == 0:
            return SendResult(
                success=True,
                message_id=body.get("message_id")
            )

        return SendResult(
            success=False,
            error=PlatformError(
                code=body.get("errcode", 0),
                message=body.get("errmsg", "Unknown error")
            ),
            retry_suggested=body.get("errcode") == WECOM_RATE_LIMIT_CODE
        )

    def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(
            max_requests=20,
            window_seconds=60,
            remaining=self._rate_limit_remaining
        )

    def get_webhook_url(self) -> str:
        return f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={self._webhook_key}"


# ============================================================================
# DingTalk Adapter
# =========================================================================


class DingTalkAdapter(PlatformAdapter):
    """Adapter for DingTalk (钉钉)."""

    @property
    def platform(self) -> str:
        return "dingtalk"

    @property
    def priority(self) -> int:
        return 2

    def __init__(self, access_token: str, secret: Optional[str] = None):
        self._access_token = access_token
        self._secret = secret

    def is_available(self) -> bool:
        return bool(self._access_token)

    def supports(self, message: UnifiedMessage) -> SupportLevel:
        msg_type = message.content.type

        fully_supported = [
            MessageType.TEXT,
            MessageType.MARKDOWN,
            "link",
            "actionCard",
            "card",  # Unified card type maps to actionCard
            MessageType.FEED  # "feed"
        ]

        if msg_type in fully_supported:
            return cast(SupportLevel, SupportLevel.FULL)
        return cast(SupportLevel, SupportLevel.NONE)

    def transform(self, message: UnifiedMessage) -> PlatformPayload:
        body: dict[str, Any] = {"msgtype": message.content.type}
        query: dict[str, str] = {}

        msg_type = message.content.type
        body_content = message.content.body

        # Add signature if secret is configured
        # Signature must be added to URL query params, not headers
        if self._secret:
            timestamp = str(int(time.time() * 1000))
            string_to_sign = f"{timestamp}\n{self._secret}"
            sign = base64.b64encode(
                hmac.new(
                    self._secret.encode("utf-8"),
                    string_to_sign.encode("utf-8"),
                    digestmod=hashlib.sha256
                ).digest()
            ).decode("utf-8")
            # Don't URL-encode here - let the sender handle it
            query["timestamp"] = timestamp
            query["sign"] = sign

        if msg_type == MessageType.TEXT:
            body["text"] = {"content": body_content.get("text", "")}
            if message.content.mentions:
                at_info: dict[str, Any] = {"isAtAll": False}
                at_mobiles: list[str] = []
                at_user_ids: list[str] = []
                for mention in message.content.mentions:
                    if mention.type == "all":
                        at_info["isAtAll"] = True
                    elif mention.type == "mobile":
                        at_mobiles.append(mention.value)
                    elif mention.type == "user_id":
                        at_user_ids.append(mention.value)
                if at_mobiles:
                    at_info["atMobiles"] = at_mobiles
                if at_user_ids:
                    at_info["atUserIds"] = at_user_ids
                body["at"] = at_info

        elif msg_type == MessageType.MARKDOWN:
            body["markdown"] = {
                "title": message.content.title or "",
                "text": body_content.get("content", "")
            }

        elif msg_type == "link":
            body["link"] = {
                "title": body_content.get("title", ""),
                "text": body_content.get("text", ""),
                "picUrl": body_content.get("image_url", ""),
                "messageUrl": body_content.get("url", "")
            }

        elif msg_type in ("actionCard", "card"):
            # DingTalk uses "actionCard" msgtype
            body["msgtype"] = "actionCard"
            card = self._transform_action_card(body_content)
            body["actionCard"] = card

        elif msg_type == "feedCard":
            body["feedCard"] = {
                "links": [
                    {
                        "title": link.get("title", ""),
                        "messageURL": link.get("url", ""),
                        "picURL": link.get("image_url", "")
                    }
                    for link in body_content.get("links", [])
                ]
            }

        # Add message UUID for deduplication
        if message.metadata.message_id:
            body["msgUuid"] = message.metadata.message_id

        return PlatformPayload(body=body, query=query)

    def _transform_action_card(self, card_body: dict[str, Any]) -> dict[str, Any]:
        """Transform card to DingTalk actionCard format."""
        config = card_body.get("config", {})

        # Get title from card_body.title or content.title
        title = card_body.get("title") or ""
        # Get description from various sources
        description = (
            card_body.get("description") or
            card_body.get("main_title", {}).get("desc") or ""
        )

        card = {
            "title": title,
            "text": description,
            "hideAvatar": config.get("hide_avatar", "0"),
            "btnOrientation": config.get("btn_orientation", "0")
        }

        # Extract text from elements
        text_parts = []
        for elem in card_body.get("elements", []):
            if elem.get("text"):
                text_parts.append(elem["text"])
        if text_parts:
            card["text"] = "\n".join(text_parts)
        elif description:
            card["text"] = description

        # Handle buttons
        actions = card_body.get("actions", [])
        if len(actions) == 1:
            action = actions[0]
            card["singleTitle"] = action.get("text", "")
            card["singleURL"] = action.get("url", "")
        elif len(actions) > 1:
            card["btns"] = [
                {
                    "title": action.get("text", ""),
                    "actionURL": action.get("url", "")
                }
                for action in actions
            ]

        return card

    def parse_response(self, response: PlatformResponse) -> SendResult:
        body = response.body

        if body.get("errcode") == 0:
            return SendResult(success=True)

        return SendResult(
            success=False,
            error=PlatformError(
                code=body.get("errcode", 0),
                message=body.get("errmsg", "Unknown error")
            ),
            retry_suggested=body.get("errcode") == DINGTALK_RATE_LIMIT_CODE
        )

    def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(
            max_requests=20,
            window_seconds=60,
            remaining=20
        )

    def get_webhook_url(self) -> str:
        return f"https://oapi.dingtalk.com/robot/send?access_token={self._access_token}"


# ============================================================================
# Feishu Adapter
# =========================================================================


class FeishuAdapter(PlatformAdapter):
    """Adapter for Feishu/Lark (飞书)."""

    @property
    def platform(self) -> str:
        return "feishu"

    @property
    def priority(self) -> int:
        return 3

    def __init__(self, webhook_id: str, secret: Optional[str] = None, timestamp_override: Optional[int] = None):
        self._webhook_id = webhook_id
        self._secret = secret
        self._timestamp_override = timestamp_override

    def is_available(self) -> bool:
        return bool(self._webhook_id)

    def supports(self, message: UnifiedMessage) -> SupportLevel:
        msg_type = message.content.type

        fully_supported = [
            MessageType.TEXT,
            "post",
            MessageType.IMAGE,
            MessageType.FILE,
            MessageType.CARD,
            "audio"
        ]

        if msg_type in fully_supported:
            return cast(SupportLevel, SupportLevel.FULL)
        return cast(SupportLevel, SupportLevel.NONE)

    def transform(self, message: UnifiedMessage) -> PlatformPayload:
        body: dict[str, Any] = {}
        warnings: list[str] = []

        msg_type = message.content.type
        body_content = message.content.body

        if msg_type == MessageType.TEXT:
            text = body_content.get("text", "")
            # Process mentions
            if message.content.mentions:
                for mention in message.content.mentions:
                    if mention.type == "all":
                        text = f"<at user_id=\"all\">所有人</at> {text}"
                    elif mention.type == "user_id":
                        display = mention.display_name or mention.value
                        text = text.replace(
                            display,
                            f"<at user_id=\"{mention.value}\">{display}</at>"
                        )
            body["msg_type"] = "text"
            body["content"] = {"text": text}

        elif msg_type == "post":
            # Sanitize markdown-like markers because Feishu post text does not render markdown
            raw = body_content.get("content", "")
            text_clean = self._sanitize_post_text(raw)
            body["msg_type"] = "post"
            body["content"] = {
                "post": {
                    "zh_cn": {
                        "title": message.content.title or "",
                        # Each paragraph is a list of elements; use "tag" per Feishu bot spec
                        "content": [[{"tag": "text", "text": text_clean}]]
                    }
                }
            }

        elif msg_type == MessageType.IMAGE:
            body["msg_type"] = "image"
            body["content"] = {"image_key": body_content.get("image_key", "")}

        elif msg_type == MessageType.CARD:
            card = self._transform_card(body_content)
            # Feishu custom bot uses msg_type "interactive" and payload key "card"
            body["msg_type"] = "interactive"
            body["card"] = card

        elif msg_type == MessageType.FILE:
            body["msg_type"] = "file"
            body["content"] = {
                "file_key": body_content.get("media_id", ""),
                "file_name": body_content.get("file_name", "")
            }

        # Add signature if secret is configured
        # According to Feishu doc: payload must include timestamp & sign fields (not headers)
        # We keep headers=None to follow the doc; tests updated accordingly.
        if self._secret:
            timestamp = str(self._timestamp_override if self._timestamp_override else int(time.time()))

            # Compute signature: key = timestamp + "\n" + secret, data = empty
            string_to_sign = f"{timestamp}\n{self._secret}"
            signature = hmac.new(
                string_to_sign.encode("utf-8"),
                b"",
                digestmod=hashlib.sha256
            ).digest()

            body["timestamp"] = timestamp
            body["sign"] = base64.b64encode(signature).decode("utf-8")

        return PlatformPayload(body=body, headers=None, warnings=warnings)

    @staticmethod
    def _sanitize_post_text(text: str) -> str:
        """Remove common markdown markers to avoid raw syntax in Feishu post."""
        # Strip bold/italic markers
        for marker in ["**", "__", "*", "_", "`"]:
            text = text.replace(marker, "")
        return text

    def _transform_card(self, card_body: dict[str, Any]) -> dict[str, Any]:
        """Transform card to Feishu format."""
        config = card_body.get("config", {})

        card: dict[str, Any] = {
            "config": {
                "wide_screen_mode": config.get("wide_screen_mode", True),
                "enable_forward": config.get("enable_forward", True)
            },
            "elements": []
        }
        elements: list[dict[str, Any]] = []

        # Transform elements
        for elem in card_body.get("elements", []):
            # If user already provides Feishu-style element (has tag), pass through
            if "tag" in elem:
                elements.append(elem)
                continue

            elem_type = elem.get("type", "div")
            if elem_type == "div":
                elements.append({
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": elem.get("text", "")
                    }
                })

        # Transform actions
        if card_body.get("actions"):
            elements.append({"tag": "hr"})
            actions_elem: dict[str, Any] = {"tag": "action", "actions": []}
            actions_list: list[dict[str, Any]] = []
            for action in card_body["actions"]:
                # Pass through if already Feishu-style
                if "tag" in action:
                    actions_list.append(action)
                    continue

                action_obj: dict[str, Any] = {
                    "tag": "button",
                    "text": {"content": action.get("text", ""), "tag": "plain_text"},
                    "type": action.get("style", "default")
                }
                if action.get("url"):
                    action_obj["url"] = action["url"]
                actions_list.append(action_obj)
            actions_elem["actions"] = actions_list
            elements.append(actions_elem)

        card["elements"] = elements
        return card

    def parse_response(self, response: PlatformResponse) -> SendResult:
        body = response.body

        if body.get("code") == 0:
            return SendResult(success=True)

        return SendResult(
            success=False,
            error=PlatformError(
                code=body.get("code", 0),
                message=body.get("msg", "Unknown error")
            ),
            retry_suggested=body.get("code") in [216429, 216629]  # Rate limit
        )

    def get_rate_limit_info(self) -> RateLimitInfo:
        return RateLimitInfo(
            max_requests=100,
            window_seconds=60,
            remaining=100
        )

    def get_webhook_url(self) -> str:
        return f"https://open.feishu.cn/open-apis/bot/v2/hook/{self._webhook_id}"


# ============================================================================
# Adapter Registry
# =========================================================================


class AdapterRegistry:
    """Registry for platform adapters."""

    def __init__(self) -> None:
        self._adapters: dict[str, PlatformAdapter] = {}

    def register(self, adapter: PlatformAdapter) -> None:
        """Register an adapter."""
        self._adapters[adapter.platform] = adapter

    def get(self, platform: str) -> Optional[PlatformAdapter]:
        """Get an adapter by platform name."""
        return self._adapters.get(platform)

    def get_all(self) -> list[PlatformAdapter]:
        """Get all registered adapters."""
        return list(self._adapters.values())

    def get_by_priority(self) -> list[PlatformAdapter]:
        """Get all adapters sorted by priority."""
        return sorted(self._adapters.values(), key=lambda a: a.priority)

    def can_send(self, message: UnifiedMessage) -> list[PlatformAdapter]:
        """Get all adapters that can send this message."""
        return [
            adapter for adapter in self._adapters.values()
            if adapter.supports(message) != SupportLevel.NONE
        ]


# Default registry
default_registry = AdapterRegistry()
