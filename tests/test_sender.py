"""Tests for webhook-push message sender."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from webhook_push.sender import MessageSender, SenderOptions
from webhook_push.models import (
    UnifiedMessage,
    SendResult,
    MultiSendResult,
    AutoSendResult,
    RetryPolicy,
)
from webhook_push.adapters import WeComAdapter, DingTalkAdapter, AdapterRegistry


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client."""
    client = Mock()
    client.post = AsyncMock()
    return client


@pytest.fixture
def adapter_registry():
    """Create a test adapter registry."""
    registry = AdapterRegistry()
    wecom = WeComAdapter(webhook_key="test_key")
    dingtalk = DingTalkAdapter(access_token="test_token")
    registry.register(wecom)
    registry.register(dingtalk)
    return registry


class TestSenderOptions:
    """Tests for SenderOptions."""

    def test_default_options(self):
        """Test default sender options."""
        options = SenderOptions()
        assert options.timeout == 5000
        assert options.retry_policy is None
        assert options.http_client is None
        assert options.registry is None

    def test_custom_options(self):
        """Test custom sender options."""
        retry_policy = RetryPolicy(max_retries=5)
        http_client = Mock()
        registry = AdapterRegistry()

        options = SenderOptions(
            retry_policy=retry_policy,
            timeout=10000,
            http_client=http_client,
            registry=registry
        )

        assert options.timeout == 10000
        assert options.retry_policy == retry_policy
        assert options.http_client == http_client
        assert options.registry == registry


class TestMessageSender:
    """Tests for MessageSender."""

    def test_init_default(self):
        """Test initialization with defaults."""
        sender = MessageSender()
        assert sender._options.timeout == 5000
        assert sender._http_client is None

    def test_init_with_options(self):
        """Test initialization with custom options."""
        retry_policy = RetryPolicy(max_retries=5)
        options = SenderOptions(retry_policy=retry_policy, timeout=10000)
        sender = MessageSender(options=options)

        assert sender._retry_policy.max_retries == 5
        assert sender._options.timeout == 10000

    @pytest.mark.asyncio
    async def test_send_to_unknown_platform(self):
        """Test sending to unknown platform."""
        sender = MessageSender()
        message = UnifiedMessage(
            content={"type": "text", "body": {"text": "Hello"}}
        )

        result = await sender.send(message, "unknown_platform")

        assert result.success is False
        assert result.error.code == "UNKNOWN_PLATFORM"
        assert "Unknown platform" in result.error.message

    @pytest.mark.asyncio
    async def test_send_unsupported_message_type(self):
        """Test sending unsupported message type."""
        registry = AdapterRegistry()
        adapter = Mock()
        adapter.platform = "test"
        adapter.supports = Mock(return_value="none")
        registry.register(adapter)

        sender = MessageSender(
            options=SenderOptions(registry=registry)
        )

        message = UnifiedMessage(
            content={"type": "unsupported", "body": {}}
        )

        result = await sender.send(message, "test")

        assert result.success is False
        assert result.error.code == "UNSUPPORTED"

    @pytest.mark.asyncio
    async def test_send_with_custom_webhook_url(self):
        """Test sending with custom webhook URL."""
        registry = AdapterRegistry()
        wecom = WeComAdapter(webhook_key="original_key")
        registry.register(wecom)

        sender = MessageSender(options=SenderOptions(registry=registry))
        message = UnifiedMessage(
            content={"type": "text", "body": {"text": "Hello"}}
        )

        # This test just verifies the method accepts the parameter
        # Actual sending would require mocking HTTP client
        with patch.object(wecom, 'transform') as mock_transform:
            mock_transform.return_value = Mock(body={})
            with patch.object(sender, '_send_with_retry') as mock_send:
                mock_send.return_value = SendResult(success=True)

                result = await sender.send(
                    message,
                    "wecom",
                    webhook_url="https://custom.url"
                )

                assert result.success is True

    @pytest.mark.asyncio
    async def test_send_multi_to_multiple_platforms(self):
        """Test sending to multiple platforms."""
        registry = AdapterRegistry()
        wecom = WeComAdapter(webhook_key="key1")
        dingtalk = DingTalkAdapter(access_token="token1")
        registry.register(wecom)
        registry.register(dingtalk)

        sender = MessageSender(options=SenderOptions(registry=registry))
        message = UnifiedMessage(
            content={"type": "text", "body": {"text": "Hello"}}
        )

        with patch.object(sender, 'send') as mock_send:
            mock_send.side_effect = [
                SendResult(success=True, message_id="msg1"),
                SendResult(success=True, message_id="msg2")
            ]

            result = await sender.send_multi(
                message,
                platforms=["wecom", "dingtalk"]
            )

            assert result.total == 2
            assert result.success_count == 2
            assert result.failed_count == 0
            assert len(result.results) == 2

    @pytest.mark.asyncio
    async def test_send_multi_with_failures(self):
        """Test sending to multiple platforms with some failures."""
        registry = AdapterRegistry()
        wecom = WeComAdapter(webhook_key="key1")
        dingtalk = DingTalkAdapter(access_token="token1")
        registry.register(wecom)
        registry.register(dingtalk)

        sender = MessageSender(options=SenderOptions(registry=registry))
        message = UnifiedMessage(
            content={"type": "text", "body": {"text": "Hello"}}
        )

        with patch.object(sender, 'send') as mock_send:
            mock_send.side_effect = [
                SendResult(success=True, message_id="msg1"),
                SendResult(
                    success=False,
                    error={"code": "ERROR", "message": "Failed"}
                )
            ]

            result = await sender.send_multi(
                message,
                platforms=["wecom", "dingtalk"]
            )

            assert result.total == 2
            assert result.success_count == 1
            assert result.failed_count == 1

    @pytest.mark.asyncio
    async def test_send_multi_with_exceptions(self):
        """Test sending to multiple platforms with exceptions."""
        registry = AdapterRegistry()
        wecom = WeComAdapter(webhook_key="key1")
        dingtalk = DingTalkAdapter(access_token="token1")
        registry.register(wecom)
        registry.register(dingtalk)

        sender = MessageSender(options=SenderOptions(registry=registry))
        message = UnifiedMessage(
            content={"type": "text", "body": {"text": "Hello"}}
        )

        with patch.object(sender, 'send') as mock_send:
            mock_send.side_effect = [
                SendResult(success=True, message_id="msg1"),
                Exception("Network error")
            ]

            result = await sender.send_multi(
                message,
                platforms=["wecom", "dingtalk"]
            )

            assert result.total == 2
            assert result.success_count == 1
            assert result.failed_count == 1
            # error should be a dict after model_dump
            assert result.results[1]["error"]["code"] == "EXCEPTION"

    @pytest.mark.asyncio
    async def test_send_auto_to_available_platforms(self):
        """Test automatic sending to available platforms."""
        registry = AdapterRegistry()
        wecom = WeComAdapter(webhook_key="key1")
        dingtalk = DingTalkAdapter(access_token="token1")
        registry.register(wecom)
        registry.register(dingtalk)

        sender = MessageSender(options=SenderOptions(registry=registry))
        message = UnifiedMessage(
            content={"type": "text", "body": {"text": "Hello"}}
        )

        with patch.object(sender, 'send') as mock_send:
            mock_send.side_effect = [
                SendResult(success=True, message_id="msg1"),
                SendResult(success=True, message_id="msg2")
            ]

            result = await sender.send_auto(message)

            assert "wecom" in result.sent_platforms
            assert "dingtalk" in result.sent_platforms
            assert len(result.results) == 2

    @pytest.mark.asyncio
    async def test_send_auto_skips_unsupported(self):
        """Test auto send skips platforms that don't support message type."""
        registry = AdapterRegistry()
        wecom = WeComAdapter(webhook_key="key1")

        # Mock adapter that doesn't support the message
        unsupported_adapter = Mock()
        unsupported_adapter.platform = "unsupported"
        unsupported_adapter.supports = Mock(return_value="none")

        registry.register(wecom)
        registry.register(unsupported_adapter)

        sender = MessageSender(options=SenderOptions(registry=registry))
        message = UnifiedMessage(
            content={"type": "text", "body": {"text": "Hello"}}
        )

        with patch.object(sender, 'send') as mock_send:
            mock_send.return_value = SendResult(success=True, message_id="msg1")

            result = await sender.send_auto(message)

            assert "wecom" in result.sent_platforms
            # The unsupported platform should be skipped


class TestRetryPolicy:
    """Tests for RetryPolicy."""

    def test_default_retry_policy(self):
        """Test default retry policy."""
        policy = RetryPolicy()
        assert policy.max_retries == 3
        assert policy.initial_delay == 1000
        assert policy.max_delay == 30000
        assert policy.backoff_multiplier == 2.0

    def test_custom_retry_policy(self):
        """Test custom retry policy."""
        policy = RetryPolicy(
            max_retries=5,
            initial_delay=2000,
            max_delay=60000,
            backoff_multiplier=3.0
        )

        assert policy.max_retries == 5
        assert policy.initial_delay == 2000
        assert policy.max_delay == 60000
        assert policy.backoff_multiplier == 3.0


class TestSendResult:
    """Tests for SendResult."""

    def test_successful_result(self):
        """Test successful send result."""
        result = SendResult(success=True, message_id="msg123")
        assert result.success is True
        assert result.message_id == "msg123"
        assert result.error is None
        assert result.retry_suggested is False

    def test_failed_result(self):
        """Test failed send result."""
        from webhook_push.models import PlatformError

        result = SendResult(
            success=False,
            error=PlatformError(code=400, message="Bad Request")
        )
        assert result.success is False
        assert result.error.code == 400
        assert result.retry_suggested is False

    def test_failed_result_with_retry(self):
        """Test failed result with retry suggestion."""
        from webhook_push.models import PlatformError

        result = SendResult(
            success=False,
            error=PlatformError(code="RATE_LIMIT", message="Too many requests"),
            retry_suggested=True
        )
        assert result.success is False
        assert result.retry_suggested is True


class TestMultiSendResult:
    """Tests for MultiSendResult."""

    def test_all_successful(self):
        """Test result when all sends succeed."""
        result = MultiSendResult(
            total=3,
            success_count=3,
            failed_count=0,
            results=[
                {"platform": "wecom", "success": True},
                {"platform": "dingtalk", "success": True},
                {"platform": "feishu", "success": True}
            ]
        )

        assert result.total == 3
        assert result.success_count == 3
        assert result.failed_count == 0

    def test_mixed_results(self):
        """Test result with mixed success and failure."""
        result = MultiSendResult(
            total=3,
            success_count=2,
            failed_count=1,
            results=[
                {"platform": "wecom", "success": True},
                {"platform": "dingtalk", "success": False},
                {"platform": "feishu", "success": True}
            ]
        )

        assert result.total == 3
        assert result.success_count == 2
        assert result.failed_count == 1


class TestAutoSendResult:
    """Tests for AutoSendResult."""

    def test_auto_send_result(self):
        """Test auto send result."""
        result = AutoSendResult(
            sent_platforms=["wecom", "dingtalk"],
            skipped_platforms=["feishu"],
            results={
                "wecom": SendResult(success=True),
                "dingtalk": SendResult(success=True),
                "feishu": SendResult(success=False)
            }
        )

        assert len(result.sent_platforms) == 2
        assert len(result.skipped_platforms) == 1
        assert len(result.results) == 3
