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

## Platform Adapters

### FeishuAdapter

Adapter for Feishu/Lark platform with signature verification support.

```python
from webhook_push import FeishuAdapter

# Without signature (not recommended for production)
adapter = FeishuAdapter(webhook_id="your-webhook-id")

# With signature verification (recommended)
adapter = FeishuAdapter(
    webhook_id="your-webhook-id",
    secret="your-signing-secret"
)
```

**Constructor Parameters:**
- `webhook_id` (str): The webhook ID from Feishu bot settings
- `secret` (str, optional): Signing secret for HMAC-SHA256 verification

**Signature Verification:**
When `secret` is provided, the adapter will:
1. Generate timestamp (current Unix timestamp)
2. Create signature string: `timestamp + "\n" + json_body`
3. Compute HMAC-SHA256 using key: `timestamp + "\n" + secret`
4. Add headers:
   - `X-Lark-Signature`: Base64-encoded signature
   - `Timestamp`: Unix timestamp

**Methods:**
- `get_webhook_url()`: Returns the V2 webhook URL
- `supports(message)`: Check if message type is supported
- `transform(message)`: Transform to Feishu format with signature
- `parse_response(response)`: Parse Feishu API response

### DingTalkAdapter

Adapter for DingTalk platform with signature verification support.

```python
from webhook_push import DingTalkAdapter

adapter = DingTalkAdapter(
    access_token="your-access-token",
    secret="your-signing-secret"  # Optional
)
```

**Signature Verification:**
When `secret` is provided, signature is added to query parameters (not headers):
- `timestamp`: Current Unix timestamp in milliseconds
- `sign`: Base64-encoded HMAC-SHA256 signature

### WeComAdapter

Adapter for Enterprise WeChat platform.

```python
from webhook_push import WeComAdapter

adapter = WeComAdapter(webhook_key="your-webhook-key")
```

**Note:** WeCom does not support signature verification for webhook messages.

## Configuration

### load_config(config_path=None)

Load configuration from YAML file.

```python
from webhook_push import load_config

# Load from default locations
config = load_config()

# Load from specific file
config = load_config("/path/to/config.yaml")

# Access platform configuration
feishu_config = config.platforms.get("feishu")
print(feishu_config.webhook_url)
print(feishu_config.secret)  # Signature secret
```

**Default Config File Locations:**
1. `webhook-push.yaml` (current directory)
2. `webhook-push.yml` (current directory)
3. `~/.webhook-push.yaml` (home directory)
4. `~/.webhook-push.yml` (home directory)

**Environment Variables:**
Config values can be overridden with environment variables:
- `FEISHU_WEBHOOK_URL`
- `FEISHU_SECRET`
- `DINGTALK_WEBHOOK_URL`
- `DINGTALK_SECRET`
- `WECOM_WEBHOOK_URL`

## CLI Reference

### send Command

Send a message to a specific platform.

```bash
# Using command line arguments
webhook-push send feishu "https://open.feishu.cn/open-apis/bot/v2/hook/xxx" \
  --secret "your-secret" \
  --content "Hello, Feishu!"

# Using config file
webhook-push send feishu \
  --config webhook-push.yaml \
  --content "Hello from config!"
```

**Options:**
- `--config, -C`: Path to config file
- `--secret, -s`: Signature verification secret
- `--type, -t`: Message type (text, markdown)
- `--title`: Message title (for markdown)
- `--content, -c`: Message content
- `--file, -f`: File containing message content
- `--json`: Output result as JSON
