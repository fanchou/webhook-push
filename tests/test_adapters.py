"""Tests for webhook-push platform adapters."""

import pytest
from webhook_push.adapters import (
    PlatformAdapter,
    WeComAdapter,
    DingTalkAdapter,
    FeishuAdapter,
    AdapterRegistry,
)
from webhook_push.models import (
    UnifiedMessage,
    SendResult,
    PlatformPayload,
    PlatformResponse,
    SupportLevel,
)


class TestWeComAdapter:
    """Tests for WeComAdapter."""

    def test_platform_identifier(self):
        """Test platform identifier."""
        adapter = WeComAdapter(webhook_key="test_key")
        assert adapter.platform == "wecom"

    def test_priority(self):
        """Test adapter priority."""
        adapter = WeComAdapter(webhook_key="test_key")
        assert adapter.priority == 1

    def test_is_available(self):
        """Test availability check."""
        adapter = WeComAdapter(webhook_key="test_key")
        assert adapter.is_available() is True

        empty_adapter = WeComAdapter(webhook_key="")
        assert empty_adapter.is_available() is False

    def test_webhook_url(self):
        """Test webhook URL generation."""
        adapter = WeComAdapter(webhook_key="abc123")
        url = adapter.get_webhook_url()
        assert "qyapi.weixin.qq.com" in url
        assert "abc123" in url

    def test_supports_text_message(self):
        """Test text message support."""
        adapter = WeComAdapter(webhook_key="test_key")
        message = UnifiedMessage(content={"type": "text", "body": {"text": "Hello"}})
        support = adapter.supports(message)
        assert support == SupportLevel.FULL

    def test_supports_markdown_message(self):
        """Test markdown message support."""
        adapter = WeComAdapter(webhook_key="test_key")
        message = UnifiedMessage(
            content={"type": "markdown", "body": {"content": "# Title"}}
        )
        support = adapter.supports(message)
        assert support == SupportLevel.FULL

    def test_supports_image_message(self):
        """Test image message support."""
        adapter = WeComAdapter(webhook_key="test_key")
        message = UnifiedMessage(
            content={"type": "image", "body": {"base64": "abc", "md5": "123"}}
        )
        support = adapter.supports(message)
        assert support == SupportLevel.FULL

    def test_supports_card_message(self):
        """Test card message support (partial)."""
        adapter = WeComAdapter(webhook_key="test_key")
        message = UnifiedMessage(
            content={"type": "card", "body": {"card_type": "text_notice"}}
        )
        support = adapter.supports(message)
        assert support == SupportLevel.PARTIAL

    def test_transform_text_message(self):
        """Test text message transformation."""
        adapter = WeComAdapter(webhook_key="test_key")
        message = UnifiedMessage(
            content={"type": "text", "body": {"text": "Hello, WeCom!"}}
        )
        payload = adapter.transform(message)

        assert isinstance(payload, PlatformPayload)
        assert payload.body["msgtype"] == "text"
        assert payload.body["text"]["content"] == "Hello, WeCom!"

    def test_transform_text_with_mentions(self):
        """Test text message with mentions."""
        adapter = WeComAdapter(webhook_key="test_key")
        message = UnifiedMessage(
            content={
                "type": "text",
                "body": {"text": "Hello everyone!"},
                "mentions": [
                    {"type": "all", "value": "@all"},
                    {"type": "mobile", "value": "13800000000"}
                ]
            }
        )
        payload = adapter.transform(message)

        assert "@all" in payload.body["text"]["mentioned_list"]
        assert "13800000000" in payload.body["text"]["mentioned_mobile_list"]

    def test_transform_markdown_message(self):
        """Test markdown message transformation."""
        adapter = WeComAdapter(webhook_key="test_key")
        message = UnifiedMessage(
            content={"type": "markdown", "body": {"content": "**Bold** text"}}
        )
        payload = adapter.transform(message)

        assert payload.body["msgtype"] == "markdown"
        assert payload.body["markdown"]["content"] == "**Bold** text"

    def test_transform_enhanced_markdown(self):
        """Test enhanced markdown (v2)."""
        adapter = WeComAdapter(webhook_key="test_key")
        message = UnifiedMessage(
            content={
                "type": "markdown",
                "body": {"content": "| Table |", "enhanced": True}
            }
        )
        payload = adapter.transform(message)

        assert payload.body["msgtype"] == "markdown_v2"

    def test_parse_success_response(self):
        """Test parsing successful response."""
        adapter = WeComAdapter(webhook_key="test_key")
        response = PlatformResponse(
            status_code=200,
            body={"errcode": 0, "errmsg": "ok", "message_id": "msg_123"}
        )
        result = adapter.parse_response(response)

        assert result.success is True
        assert result.message_id == "msg_123"

    def test_parse_error_response(self):
        """Test parsing error response."""
        adapter = WeComAdapter(webhook_key="test_key")
        response = PlatformResponse(
            status_code=200,
            body={"errcode": 40001, "errmsg": "Invalid credential"}
        )
        result = adapter.parse_response(response)

        assert result.success is False
        assert result.error.code == 40001
        assert result.error.message == "Invalid credential"

    def test_parse_rate_limit_response(self):
        """Test parsing rate limit response."""
        adapter = WeComAdapter(webhook_key="test_key")
        response = PlatformResponse(
            status_code=200,
            body={"errcode": 60008, "errmsg": "Rate limit exceeded"}
        )
        result = adapter.parse_response(response)

        assert result.success is False
        assert result.retry_suggested is True

    def test_get_rate_limit_info(self):
        """Test rate limit information."""
        adapter = WeComAdapter(webhook_key="test_key")
        info = adapter.get_rate_limit_info()

        assert info.max_requests == 20
        assert info.window_seconds == 60
        assert info.remaining == 20


class TestDingTalkAdapter:
    """Tests for DingTalkAdapter."""

    def test_platform_identifier(self):
        """Test platform identifier."""
        adapter = DingTalkAdapter(access_token="test_token")
        assert adapter.platform == "dingtalk"

    def test_priority(self):
        """Test adapter priority."""
        adapter = DingTalkAdapter(access_token="test_token")
        assert adapter.priority == 2

    def test_is_available(self):
        """Test availability check."""
        adapter = DingTalkAdapter(access_token="test_token")
        assert adapter.is_available() is True

        empty_adapter = DingTalkAdapter(access_token="")
        assert empty_adapter.is_available() is False

    def test_webhook_url(self):
        """Test webhook URL generation."""
        adapter = DingTalkAdapter(access_token="abc123")
        url = adapter.get_webhook_url()
        assert "oapi.dingtalk.com" in url
        assert "abc123" in url

    def test_supports_text_message(self):
        """Test text message support."""
        adapter = DingTalkAdapter(access_token="test_token")
        message = UnifiedMessage(content={"type": "text", "body": {"text": "Hello"}})
        support = adapter.supports(message)
        assert support == SupportLevel.FULL

    def test_supports_markdown_message(self):
        """Test markdown message support."""
        adapter = DingTalkAdapter(access_token="test_token")
        message = UnifiedMessage(
            content={"type": "markdown", "body": {"content": "# Title"}}
        )
        support = adapter.supports(message)
        assert support == SupportLevel.FULL

    def test_transform_text_message(self):
        """Test text message transformation."""
        adapter = DingTalkAdapter(access_token="test_token")
        message = UnifiedMessage(
            content={"type": "text", "body": {"text": "Hello, DingTalk!"}}
        )
        payload = adapter.transform(message)

        assert payload.body["msgtype"] == "text"
        assert payload.body["text"]["content"] == "Hello, DingTalk!"

    def test_transform_text_with_at_all(self):
        """Test text message with @all."""
        adapter = DingTalkAdapter(access_token="test_token")
        message = UnifiedMessage(
            content={
                "type": "text",
                "body": {"text": "Hello everyone!"},
                "mentions": [{"type": "all", "value": "@all"}]
            }
        )
        payload = adapter.transform(message)

        assert payload.body["at"]["isAtAll"] is True

    def test_transform_markdown_with_title(self):
        """Test markdown message with title."""
        adapter = DingTalkAdapter(access_token="test_token")
        message = UnifiedMessage(
            content={
                "type": "markdown",
                "title": "Report",
                "body": {"content": "**Bold** text"}
            }
        )
        payload = adapter.transform(message)

        assert payload.body["markdown"]["title"] == "Report"
        assert payload.body["markdown"]["text"] == "**Bold** text"

    def test_signature_with_secret(self):
        """Test signature generation when secret is provided."""
        adapter = DingTalkAdapter(access_token="test_token", secret="SEC123")
        message = UnifiedMessage(
            content={"type": "text", "body": {"text": "Signed message"}}
        )
        payload = adapter.transform(message)

        # Signature is added to query params, not headers
        assert payload.query is not None
        assert "timestamp" in payload.query
        assert "sign" in payload.query

    def test_parse_success_response(self):
        """Test parsing successful response."""
        adapter = DingTalkAdapter(access_token="test_token")
        response = PlatformResponse(
            status_code=200,
            body={"errcode": 0, "errmsg": "ok"}
        )
        result = adapter.parse_response(response)

        assert result.success is True

    def test_parse_error_response(self):
        """Test parsing error response."""
        adapter = DingTalkAdapter(access_token="test_token")
        response = PlatformResponse(
            status_code=200,
            body={"errcode": 40001, "errmsg": "Invalid credential"}
        )
        result = adapter.parse_response(response)

        assert result.success is False
        assert result.error.code == 40001
        assert result.retry_suggested is False

    def test_get_rate_limit_info(self):
        """Test rate limit information."""
        adapter = DingTalkAdapter(access_token="test_token")
        info = adapter.get_rate_limit_info()

        assert info.max_requests == 20
        assert info.window_seconds == 60


class TestFeishuAdapter:
    """Tests for FeishuAdapter."""

    def test_platform_identifier(self):
        """Test platform identifier."""
        adapter = FeishuAdapter(webhook_id="test_id")
        assert adapter.platform == "feishu"

    def test_priority(self):
        """Test adapter priority."""
        adapter = FeishuAdapter(webhook_id="test_id")
        assert adapter.priority == 3

    def test_is_available(self):
        """Test availability check."""
        adapter = FeishuAdapter(webhook_id="test_id")
        assert adapter.is_available() is True

        empty_adapter = FeishuAdapter(webhook_id="")
        assert empty_adapter.is_available() is False

    def test_webhook_url(self):
        """Test webhook URL generation."""
        adapter = FeishuAdapter(webhook_id="abc123")
        url = adapter.get_webhook_url()
        assert "open.feishu.cn" in url
        assert "abc123" in url

    def test_supports_text_message(self):
        """Test text message support."""
        adapter = FeishuAdapter(webhook_id="test_id")
        message = UnifiedMessage(content={"type": "text", "body": {"text": "Hello"}})
        support = adapter.supports(message)
        assert support == SupportLevel.FULL

    def test_supports_card_message(self):
        """Test card message support."""
        adapter = FeishuAdapter(webhook_id="test_id")
        message = UnifiedMessage(
            content={"type": "card", "body": {"card_type": "interactive"}}
        )
        support = adapter.supports(message)
        assert support == SupportLevel.FULL

    def test_transform_text_message(self):
        """Test text message transformation."""
        adapter = FeishuAdapter(webhook_id="test_id")
        message = UnifiedMessage(
            content={"type": "text", "body": {"text": "Hello, Feishu!"}}
        )
        payload = adapter.transform(message)

        assert payload.body["msg_type"] == "text"
        assert payload.body["content"]["text"] == "Hello, Feishu!"

    def test_transform_text_with_mention_all(self):
        """Test text message with @all mention."""
        adapter = FeishuAdapter(webhook_id="test_id")
        message = UnifiedMessage(
            content={
                "type": "text",
                "body": {"text": "Hello everyone!"},
                "mentions": [{"type": "all", "value": "@all"}]
            }
        )
        payload = adapter.transform(message)

        assert "<at id=all></at>" in payload.body["content"]["text"]

    def test_parse_success_response(self):
        """Test parsing successful response."""
        adapter = FeishuAdapter(webhook_id="test_id")
        response = PlatformResponse(
            status_code=200,
            body={"code": 0, "msg": "success"}
        )
        result = adapter.parse_response(response)

        assert result.success is True

    def test_parse_error_response(self):
        """Test parsing error response."""
        adapter = FeishuAdapter(webhook_id="test_id")
        response = PlatformResponse(
            status_code=200,
            body={"code": 216429, "msg": "Rate limit"}
        )
        result = adapter.parse_response(response)

        assert result.success is False
        assert result.retry_suggested is True

    def test_get_rate_limit_info(self):
        """Test rate limit information."""
        adapter = FeishuAdapter(webhook_id="test_id")
        info = adapter.get_rate_limit_info()

        assert info.max_requests == 100
        assert info.window_seconds == 60


class TestAdapterRegistry:
    """Tests for AdapterRegistry."""

    def test_register_adapter(self):
        """Test registering an adapter."""
        registry = AdapterRegistry()
        adapter = WeComAdapter(webhook_key="test_key")

        registry.register(adapter)
        assert registry.get("wecom") == adapter

    def test_get_nonexistent_adapter(self):
        """Test getting non-existent adapter."""
        registry = AdapterRegistry()
        assert registry.get("unknown") is None

    def test_get_all_adapters(self):
        """Test getting all adapters."""
        registry = AdapterRegistry()
        wecom = WeComAdapter(webhook_key="key1")
        dingtalk = DingTalkAdapter(access_token="token1")
        feishu = FeishuAdapter(webhook_id="id1")

        registry.register(wecom)
        registry.register(dingtalk)
        registry.register(feishu)

        adapters = registry.get_all()
        assert len(adapters) == 3

    def test_get_by_priority(self):
        """Test getting adapters sorted by priority."""
        registry = AdapterRegistry()
        feishu = FeishuAdapter(webhook_id="id1")
        wecom = WeComAdapter(webhook_key="key1")
        dingtalk = DingTalkAdapter(access_token="token1")

        registry.register(wecom)  # priority 1
        registry.register(dingtalk)  # priority 2
        registry.register(feishu)  # priority 3

        sorted_adapters = registry.get_by_priority()
        assert sorted_adapters[0].platform == "wecom"
        assert sorted_adapters[1].platform == "dingtalk"
        assert sorted_adapters[2].platform == "feishu"

    def test_can_send(self):
        """Test getting adapters that can send a message."""
        registry = AdapterRegistry()
        wecom = WeComAdapter(webhook_key="key1")
        dingtalk = DingTalkAdapter(access_token="token1")
        feishu = FeishuAdapter(webhook_id="id1")

        registry.register(wecom)
        registry.register(dingtalk)
        registry.register(feishu)

        # Text message is supported by all platforms
        message = UnifiedMessage(
            content={"type": "text", "body": {"text": "Hello"}}
        )
        capable = registry.can_send(message)
        assert len(capable) == 3

        # Card message is supported by WeCom and Feishu only
        card_message = UnifiedMessage(
            content={"type": "card", "body": {"card_type": "interactive"}}
        )
        capable_for_card = registry.can_send(card_message)
        assert len(capable_for_card) >= 1  # At least Feishu
