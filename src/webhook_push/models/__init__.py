"""Message models for webhook-push skill.

This module defines the unified message model that abstracts platform-specific
differences, allowing a single interface to send messages to WeCom, DingTalk,
and Feishu platforms.
"""

from __future__ import annotations

from typing import Any, Optional, Union

from pydantic import BaseModel

# ============================================================================
# Enums (using str subclass for better serialization)
# =========================================================================


class MessageType(str):
    """Supported message types."""

    TEXT = "text"
    MARKDOWN = "markdown"
    IMAGE = "image"
    LINK = "link"
    CARD = "card"
    FILE = "file"
    FEED = "feed"


class MessagePriority(str):
    """Message priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class CardType(str):
    """Card message types for different platforms."""

    # Enterprise WeCom
    TEXT_NOTICE = "text_notice"
    NEWS_SHOW = "news_show"

    # DingTalk
    ACTION_CARD_SINGLE = "single"
    ACTION_CARD_MULTI = "multi"

    # Feishu
    INTERACTIVE = "interactive"
    TEMPLATE = "template"


class ActionType(str):
    """Action types for card buttons."""

    BUTTON = "button"
    LINK = "link"
    CALLBACK = "callback"


class MentionType(str):
    """Mention types."""

    USER_ID = "user_id"
    MOBILE = "mobile"
    DEPARTMENT = "department"
    ALL = "all"


class SupportLevel(str):
    """Platform support level for a message type."""

    FULL = "full"
    PARTIAL = "partial"
    NONE = "none"


# ============================================================================
# Message Models
# =========================================================================


class MessageMetadata(BaseModel):
    """Metadata for a message."""

    message_id: Optional[str] = None
    correlation_id: Optional[str] = None
    priority: str = "normal"
    source: Optional[str] = None
    created_at: Optional[str] = None


class Mention(BaseModel):
    """@Mention configuration."""

    type: str
    value: str
    display_name: Optional[str] = None


class TextBody(BaseModel):
    """Text message body."""

    text: str


class MarkdownBody(BaseModel):
    """Markdown message body."""

    content: str
    enhanced: bool = False


class ImageBody(BaseModel):
    """Image message body."""

    url: Optional[str] = None
    base64: Optional[str] = None
    md5: Optional[str] = None
    alt: Optional[str] = None


class LinkBody(BaseModel):
    """Link message body."""

    title: str
    text: Optional[str] = None
    url: str
    image_url: Optional[str] = None


class FeedLink(BaseModel):
    """Feed link item."""

    title: str
    url: str
    image_url: str


class CardAction(BaseModel):
    """Card action/button."""

    type: str = "button"
    text: str
    url: Optional[str] = None
    value: Optional[dict[str, Any]] = None
    style: str = "default"


class CardElement(BaseModel):
    """Card element base."""

    type: str
    text: Optional[str] = None


class CardConfig(BaseModel):
    """Card configuration."""

    wide_screen_mode: Optional[bool] = None
    enable_forward: Optional[bool] = None
    hide_avatar: Optional[str] = None
    btn_orientation: Optional[str] = None


class CardBody(BaseModel):
    """Card message body."""

    card_type: str
    config: Optional[CardConfig] = None
    elements: list[CardElement] = []
    actions: Optional[list[CardAction]] = None


class WeComSource(BaseModel):
    """WeCom template card source info."""

    icon_url: Optional[str] = None
    desc: Optional[str] = None
    desc_color: Optional[int] = None


class WeComEmphasisContent(BaseModel):
    """WeCom template card emphasis content."""

    title: str
    desc: Optional[str] = None


class WeComQuoteArea(BaseModel):
    """WeCom template card quote area."""

    type: int = 1
    url: Optional[str] = None
    appid: Optional[str] = None
    pagepath: Optional[str] = None
    title: Optional[str] = None
    quote_text: Optional[str] = None


class WeComHorizontalContent(BaseModel):
    """WeCom template card horizontal content item."""

    keyname: str
    value: str
    type: Optional[int] = None
    url: Optional[str] = None
    media_id: Optional[str] = None


class WeComJumpList(BaseModel):
    """WeCom template card jump list item."""

    type: int = 1
    url: Optional[str] = None
    title: str


class WeComCardAction(BaseModel):
    """WeCom template card action."""

    type: int = 1
    url: Optional[str] = None


class WeComTemplateCard(BaseModel):
    """WeCom template card body.

    Supports text_notice and news_show card types.
    """

    card_type: str = "text_notice"
    source: Optional[WeComSource] = None
    main_title: Optional[dict[str, str]] = None
    emphasis_content: Optional[WeComEmphasisContent] = None
    quote_area: Optional[WeComQuoteArea] = None
    sub_title_text: Optional[str] = None
    horizontal_content_list: Optional[list[WeComHorizontalContent]] = None
    jump_list: Optional[list[WeComJumpList]] = None
    card_action: Optional[WeComCardAction] = None


class FileBody(BaseModel):
    """File message body."""

    url: Optional[str] = None
    media_id: Optional[str] = None
    file_name: Optional[str] = None
    file_type: Optional[str] = None


class FeedBody(BaseModel):
    """Feed (multiple links) message body."""

    links: list[FeedLink]


class MessageContent(BaseModel):
    """Message content container."""

    type: str
    title: Optional[str] = None
    body: Any
    media: Optional[list[dict[str, Any]]] = None
    actions: Optional[list[CardAction]] = None
    mentions: Optional[list[Mention]] = None


class UnifiedMessage(BaseModel):
    """Unified message interface."""

    metadata: MessageMetadata = MessageMetadata()
    content: MessageContent
    options: Optional[dict[str, Any]] = None


# ============================================================================
# Result Models
# =========================================================================


class PlatformError(BaseModel):
    """Platform-specific error."""

    code: Union[int, str]
    message: str
    details: Optional[dict[str, Any]] = None


class SendResult(BaseModel):
    """Result of a send operation."""

    success: bool
    message_id: Optional[str] = None
    error: Optional[PlatformError] = None
    retry_suggested: bool = False
    metadata: Optional[dict[str, Any]] = None


class PlatformPayload(BaseModel):
    """Platform-specific payload after transformation."""

    body: Union[str, dict[str, Any]]
    headers: Optional[dict[str, str]] = None
    query: Optional[dict[str, str]] = None
    warnings: Optional[list[str]] = None


class PlatformResponse(BaseModel):
    """Raw platform response."""

    status_code: int
    body: dict[str, Any]
    headers: Optional[dict[str, str]] = None


class RateLimitInfo(BaseModel):
    """Rate limit information for a platform."""

    max_requests: int
    window_seconds: int
    remaining: int
    reset_at: Optional[str] = None


class MultiSendResult(BaseModel):
    """Result of multi-platform sending."""

    total: int
    success_count: int
    failed_count: int
    results: list[dict[str, Any]]


class AutoSendResult(BaseModel):
    """Result of automatic platform selection."""

    sent_platforms: list[str]
    skipped_platforms: list[str]
    results: dict[str, SendResult]


# ============================================================================
# Configuration Models
# =========================================================================


class PlatformConfig(BaseModel):
    """Platform-specific configuration."""

    webhook_url: str
    secret: Optional[str] = None
    enabled: bool = True


class RetryPolicy(BaseModel):
    """Retry policy configuration."""

    max_retries: int = 3
    initial_delay: int = 1000
    max_delay: int = 30000
    backoff_multiplier: float = 2.0


class WebhookPushConfig(BaseModel):
    """Main configuration for webhook-push."""

    platforms: dict[str, PlatformConfig] = {}
    retry: RetryPolicy = RetryPolicy()
    default_timeout: int = 5000


# ============================================================================
# Export all models
# =========================================================================


__all__ = [
    # Enums
    "MessageType",
    "MessagePriority",
    "CardType",
    "ActionType",
    "MentionType",
    "SupportLevel",

    # Message Models
    "MessageMetadata",
    "MessageContent",
    "Mention",
    "TextBody",
    "MarkdownBody",
    "ImageBody",
    "LinkBody",
    "FeedLink",
    "CardAction",
    "CardElement",
    "CardConfig",
    "CardBody",
    "FileBody",
    "FeedBody",
    "UnifiedMessage",

    # Result Models
    "PlatformError",
    "SendResult",
    "PlatformPayload",
    "PlatformResponse",
    "RateLimitInfo",
    "MultiSendResult",
    "AutoSendResult",

    # Config Models
    "PlatformConfig",
    "RetryPolicy",
    "WebhookPushConfig",
]
