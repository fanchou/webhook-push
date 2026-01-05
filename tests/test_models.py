"""Tests for webhook-push message models."""

import pytest
from webhook_push.models import (
    UnifiedMessage,
    MessageMetadata,
    MessageContent,
    TextBody,
    MarkdownBody,
    ImageBody,
    LinkBody,
    CardBody,
    FeedBody,
    CardAction,
    CardElement,
    Mention,
    SendResult,
    PlatformPayload,
    RateLimitInfo,
)


class TestMessageMetadata:
    """Tests for MessageMetadata."""

    def test_default_values(self):
        """Test default metadata values."""
        metadata = MessageMetadata()
        assert metadata.priority == "normal"
        assert metadata.message_id is None
        assert metadata.correlation_id is None

    def test_custom_values(self):
        """Test custom metadata values."""
        metadata = MessageMetadata(
            message_id="msg_001",
            correlation_id="corr_001",
            priority="high",
            source="test"
        )
        assert metadata.message_id == "msg_001"
        assert metadata.correlation_id == "corr_001"
        assert metadata.priority == "high"
        assert metadata.source == "test"


class TestTextBody:
    """Tests for TextBody."""

    def test_create_text_body(self):
        """Test creating a text body."""
        body = TextBody(text="Hello, world!")
        assert body.text == "Hello, world!"

    def test_text_body_required(self):
        """Test that text is required."""
        with pytest.raises(Exception):
            TextBody()


class TestMarkdownBody:
    """Tests for MarkdownBody."""

    def test_create_markdown_body(self):
        """Test creating a markdown body."""
        body = MarkdownBody(
            content="# Hello\nThis is **bold** text"
        )
        assert "bold" in body.content
        assert body.enhanced is False

    def test_enhanced_markdown(self):
        """Test enhanced markdown flag."""
        body = MarkdownBody(
            content="| Table | Test |",
            enhanced=True
        )
        assert body.enhanced is True


class TestImageBody:
    """Tests for ImageBody."""

    def test_image_with_url(self):
        """Test image with URL."""
        body = ImageBody(
            url="https://example.com/image.png",
            alt="Test image"
        )
        assert body.url == "https://example.com/image.png"
        assert body.alt == "Test image"

    def test_image_with_base64(self):
        """Test image with base64."""
        body = ImageBody(
            base64="data:image/png;base64,abc123",
            md5="abc123"
        )
        assert body.base64 == "data:image/png;base64,abc123"
        assert body.md5 == "abc123"


class TestLinkBody:
    """Tests for LinkBody."""

    def test_create_link_body(self):
        """Test creating a link body."""
        body = LinkBody(
            title="Example",
            text="Click here",
            url="https://example.com",
            image_url="https://example.com/cover.png"
        )
        assert body.title == "Example"
        assert body.url == "https://example.com"


class TestCardBody:
    """Tests for CardBody."""

    def test_create_card_body(self):
        """Test creating a card body."""
        card = CardBody(
            card_type="interactive",
            elements=[
                CardElement(type="div", text="Hello"),
                CardElement(type="div", text="World")
            ],
            actions=[
                CardAction(type="button", text="Click me", url="https://example.com")
            ]
        )
        assert card.card_type == "interactive"
        assert len(card.elements) == 2
        assert len(card.actions) == 1

    def test_card_with_config(self):
        """Test card with config."""
        from webhook_push.models import CardConfig

        card = CardBody(
            card_type="single",
            config=CardConfig(
                wide_screen_mode=True,
                enable_forward=True
            )
        )
        assert card.config.wide_screen_mode is True


class TestFeedBody:
    """Tests for FeedBody."""

    def test_create_feed_body(self):
        """Test creating a feed body."""
        feed = FeedBody(
            links=[
                {"title": "Link 1", "url": "https://1.com", "image_url": "https://1.com/img.png"},
                {"title": "Link 2", "url": "https://2.com", "image_url": "https://2.com/img.png"},
            ]
        )
        assert len(feed.links) == 2


class TestMention:
    """Tests for Mention."""

    def test_mention_all(self):
        """Test @all mention."""
        mention = Mention(type="all", value="@all")
        assert mention.type == "all"

    def test_mention_user(self):
        """Test user mention."""
        mention = Mention(
            type="mobile",
            value="13800000000",
            display_name="Zhang San"
        )
        assert mention.type == "mobile"
        assert mention.display_name == "Zhang San"


class TestUnifiedMessage:
    """Tests for UnifiedMessage."""

    def test_create_text_message(self):
        """Test creating a unified text message."""
        message = UnifiedMessage(
            content={
                "type": "text",
                "body": {"text": "Hello, world!"}
            }
        )
        assert message.content.type == "text"
        assert message.content.body["text"] == "Hello, world!"

    def test_create_markdown_message(self):
        """Test creating a unified markdown message."""
        message = UnifiedMessage(
            metadata={"message_id": "msg_001"},
            content={
                "type": "markdown",
                "title": "Report",
                "body": {"content": "# Daily Report"}
            }
        )
        assert message.metadata.message_id == "msg_001"
        assert message.content.type == "markdown"
        assert message.content.title == "Report"

    def test_create_card_message(self):
        """Test creating a unified card message."""
        message = UnifiedMessage(
            content={
                "type": "card",
                "body": {
                    "card_type": "interactive",
                    "elements": [{"type": "div", "text": "Alert"}],
                    "actions": [
                        {"type": "button", "text": "View", "url": "https://example.com"}
                    ]
                }
            }
        )
        assert message.content.type == "card"
        assert message.content.body["card_type"] == "interactive"


class TestSendResult:
    """Tests for SendResult."""

    def test_success_result(self):
        """Test successful result."""
        result = SendResult(
            success=True,
            message_id="msg_123"
        )
        assert result.success is True
        assert result.message_id == "msg_123"
        assert result.error is None

    def test_error_result(self):
        """Test error result."""
        from webhook_push.models import PlatformError

        result = SendResult(
            success=False,
            error=PlatformError(
                code=30001,
                message="Rate limit exceeded"
            ),
            retry_suggested=True
        )
        assert result.success is False
        assert result.error.code == 30001
        assert result.retry_suggested is True


class TestPlatformPayload:
    """Tests for PlatformPayload."""

    def test_payload_with_warnings(self):
        """Test payload with warnings."""
        payload = PlatformPayload(
            body={"msgtype": "text", "text": {"content": "Hello"}},
            headers={"Content-Type": "application/json"},
            warnings=["Some feature not supported"]
        )
        assert payload.body["msgtype"] == "text"
        assert "Content-Type" in payload.headers
        assert len(payload.warnings) == 1


class TestRateLimitInfo:
    """Tests for RateLimitInfo."""

    def test_rate_limit_info(self):
        """Test rate limit info."""
        info = RateLimitInfo(
            max_requests=20,
            window_seconds=60,
            remaining=15
        )
        assert info.max_requests == 20
        assert info.remaining == 15
