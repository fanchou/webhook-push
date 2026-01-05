# API Reference

This document provides a quick reference for the webhook-push API.

## MessageSender

The main class for sending messages.

### Constructor

```python
from webhook_push import MessageSender, SenderOptions, RetryPolicy

sender = MessageSender(
    options=SenderOptions(
        retry_policy=RetryPolicy(
            max_retries=3,
            initial_delay=1000,
            max_delay=30000,
            backoff_multiplier=2.0
        ),
        timeout=5000
    )
)
```

### Methods

#### send(message, platform, webhook_url=None)

Send a message to a specific platform.

```python
from webhook_push import UnifiedMessage

message = UnifiedMessage(
    content={
        "type": "text",
        "body": {"text": "Hello!"}
    }
)

result = await sender.send(
    message,
    "dingtalk",
    webhook_url="https://oapi.dingtalk.com/robot/send?access_token=xxx"
)
```

**Parameters:**
- `message`: UnifiedMessage - The message to send
- `platform`: str - Platform name ("wecom", "dingtalk", "feishu")
- `webhook_url`: str - Optional webhook URL override

**Returns:** SendResult

#### send_multi(message, platforms, webhook_urls=None)

Send a message to multiple platforms.

```python
result = await sender.send_multi(
    message,
    platforms=["wecom", "dingtalk", "feishu"],
    webhook_urls={
        "wecom": "https://...",
        "dingtalk": "https://...",
        "feishu": "https://..."
    }
)
```

**Returns:** MultiSendResult

#### send_auto(message)

Send to all available platforms.

```python
result = await sender.send_auto(message)
print(f"Sent to: {result.sent_platforms}")
print(f"Skipped: {result.skipped_platforms}")
```

**Returns:** AutoSendResult

## UnifiedMessage

The main message class.

```python
message = UnifiedMessage(
    metadata=MessageMetadata(
        message_id="unique-id",
        correlation_id="correlation-id",
        priority="normal"
    ),
    content=MessageContent(
        type="markdown",
        title="Optional Title",
        body=MarkdownBody(content="# Hello"),
        mentions=[...]
    )
)
```

## SendResult

Response from send operations.

```python
result = SendResult(
    success: bool,
    message_id: Optional[str] = None,
    error: Optional[PlatformError] = None,
    retry_suggested: bool = False
)

if result.success:
    print(f"Sent: {result.message_id}")
else:
    print(f"Error: {result.error}")
```

## PlatformAdapter

Internal class for platform-specific implementations.

### Supported Platforms

| Platform | Priority | Supports |
|----------|----------|----------|
| wecom | 1 | text, markdown, image, news, file, voice, card |
| dingtalk | 2 | text, markdown, link, actionCard, feedCard |
| feishu | 3 | text, post, image, file, card, audio |

### Rate Limits

| Platform | Max Requests | Window |
|----------|--------------|--------|
| WeCom | 20 | 60s |
| DingTalk | 20 | 60s |
| Feishu | 100 | 60s |

## Error Codes

| Code | Meaning | Retry? |
|------|---------|--------|
| UNKNOWN_PLATFORM | Invalid platform name | No |
| UNSUPPORTED | Message type not supported | No |
| RATE_LIMIT | Rate limit exceeded | Yes |
| NETWORK_ERROR | Network failure | Yes |
| PLATFORM_ERROR | Platform returned error | Depends |

## CLI Commands

```bash
# Send a message
webhook-push send <platform> <webhook-url> --content "Hello!"

# Send to multiple platforms
webhook-push send-multi <platform1> <platform2> ... --content "Hello!"

# Send to all platforms
webhook-push send-auto --content "Hello!"

# Show platform info
webhook-push info <platform>
```

## Examples

### Text Message with Mentions

```python
message = UnifiedMessage(
    content={
        "type": "text",
        "body": {"text": "Meeting at 3pm"},
        "mentions": [
            {"type": "all"}  # @all
        ]
    }
)
```

### Markdown Report

```python
message = UnifiedMessage(
    content={
        "type": "markdown",
        "title": "Daily Report",
        "body": {
            "content": """# Report

## Metrics
- Users: 128
- Revenue: $5,000

> Last updated: 18:00"""
        }
    }
)
```

### Interactive Card

```python
message = UnifiedMessage(
    content={
        "type": "card",
        "body": {
            "card_type": "interactive",
            "elements": [{"type": "div", "text": "Review required"}],
            "actions": [
                {"type": "button", "text": "Approve", "url": "...", "style": "primary"},
                {"type": "button", "text": "Reject", "url": "..."}
            ]
        }
    }
)
```
