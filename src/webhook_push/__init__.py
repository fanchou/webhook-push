"""Webhook Push Skill - Unified messaging for enterprise platforms."""

__version__ = "0.1.0"

# Import main classes for easy access
from webhook_push.adapters import (
    AdapterRegistry,
    DingTalkAdapter,
    FeishuAdapter,
    WeComAdapter,
)
from webhook_push.models import (
    AutoSendResult,
    MessageContent,
    MessageMetadata,
    MultiSendResult,
    PlatformConfig,
    RetryPolicy,
    SendResult,
    UnifiedMessage,
    WebhookPushConfig,
)
from webhook_push.sender import MessageSender, SenderOptions

__all__ = [
    # Version
    "__version__",

    # Models
    "UnifiedMessage",
    "MessageMetadata",
    "MessageContent",
    "SendResult",
    "MultiSendResult",
    "AutoSendResult",
    "RetryPolicy",
    "PlatformConfig",
    "WebhookPushConfig",

    # Sender
    "MessageSender",
    "SenderOptions",

    # Adapters
    "WeComAdapter",
    "DingTalkAdapter",
    "FeishuAdapter",
    "AdapterRegistry",
]
