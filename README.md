# Webhook Push Skill

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

Unified webhook messaging skill for WeCom (企业微信), DingTalk (钉钉), and Feishu (飞书) platforms.

## Overview

This skill provides a unified interface for sending webhook notifications to three major Chinese enterprise communication platforms:

- **WeCom (企业微信)** - Enterprise WeChat
- **DingTalk (钉钉)** - Alibaba's enterprise communication platform
- **Feishu (飞书)** - ByteDance's collaboration platform

## Features

- **Unified Message Model** - Send messages using a single, platform-agnostic interface
- **Multi-platform Support** - WeCom, DingTalk, and Feishu
- **Rich Message Types** - Text, Markdown, Image, Link, Card, File, Feed
- **Automatic Conversion** - Messages are automatically converted to platform-specific formats
- **Graceful Degradation** - Unsupported features are automatically downgraded
- **Retry Mechanism** - Built-in exponential backoff retry logic
- **Rate Limiting** - Platform-specific rate limit handling

## Installation

```bash
pip install webhook-push
```

## Quick Start

```python
from webhook_push import MessageSender, UnifiedMessage

# Create a text message
message = UnifiedMessage(
    content={
        "type": "text",
        "body": {"text": "Hello from webhook-push!"}
    }
)

# Send to a specific platform
sender = MessageSender()
result = await sender.send(message, "dingtalk", webhook_url="https://oapi.dingtalk.com/robot/send?access_token=xxx")
print(result)
```

## Documentation

See the following documents for detailed information:

- [Design Document](references/webhook-push-skill-design.md) - Complete design specification
- [Unified Message Design](references/webhook-push-unified-message-design.md) - Message model and API design
- [API Reference](references/api-reference.md) - Detailed API documentation

## Usage Examples

### Text Message

```python
from webhook_push import MessageSender, UnifiedMessage

message = UnifiedMessage(
    metadata={"message_id": "msg_001"},
    content={
        "type": "text",
        "title": "Notification",
        "body": {"text": "This is a test message"},
        "mentions": [{"type": "mobile", "value": "13800000000"}]
    }
)
```

### Markdown Message

```python
message = UnifiedMessage(
    content={
        "type": "markdown",
        "title": "Daily Report",
        "body": {
            "content": """# Daily Report

## Metrics
- **New Users**: 128
- **Active Users**: 3,421

> Last updated: 18:00"""
        }
    }
)
```

### Card Message

```python
message = UnifiedMessage(
    content={
        "type": "card",
        "body": {
            "card_type": "interactive",
            "config": {"wide_screen_mode": True},
            "elements": [
                {"type": "div", "text": "**Alert**: High CPU usage"}
            ],
            "actions": [
                {
                    "type": "button",
                    "text": "View Details",
                    "url": "https://example.com/alerts",
                    "style": "primary"
                }
            ]
        }
    }
)
```

### WeCom Template Card (text_notice)

```python
from webhook_push import UnifiedMessage, MessageContent

message = UnifiedMessage(
    content=MessageContent(
        type="card",
        body={
            "card_type": "text_notice",
            "title": "系统告警",
            "description": "CPU使用率超过阈值",
            "emphasis": {
                "title": "95%",
                "desc": "当前CPU使用率"
            },
            "horizontal_content_list": [
                {"keyname": "服务器", "value": "web-01"},
                {"keyname": "阈值", "value": "80%"}
            ],
            "jump_list": [
                {"type": 1, "url": "https://example.com/alerts", "title": "查看详情"}
            ],
            "action": {"type": 1, "url": "https://example.com/alerts"}
        }
    )
)

result = await sender.send(message, "wecom")
```

### WeCom News (Article Card)

```python
message = UnifiedMessage(
    content={
        "type": "news",
        "body": {
            "links": [
                {
                    "title": "技术分享: Webhook 最佳实践",
                    "description": "了解如何设计可靠的 webhook 系统",
                    "url": "https://example.com/article",
                    "image_url": "https://example.com/cover.jpg"
                }
            ]
        }
    }
)

result = await sender.send(message, "wecom")
```

### DingTalk Action Card (single button)

```python
message = UnifiedMessage(
    content=MessageContent(
        type="card",
        body={
            "card_type": "single",
            "config": {"hide_avatar": "0"},
            "title": "审批请求",
            "elements": [{"type": "div", "text": "您有一个新的审批请求待处理"}],
            "actions": [
                {"text": "立即审批", "url": "https://example.com/approve", "style": "positive"}
            ]
        }
    )
)

result = await sender.send(message, "dingtalk")
```

### DingTalk Action Card (multiple buttons)

```python
message = UnifiedMessage(
    content=MessageContent(
        type="card",
        body={
            "card_type": "multi",
            "config": {"hide_avatar": "0", "btn_orientation": "1"},
            "title": "满意度调查",
            "elements": [{"type": "div", "text": "请对本次服务进行评价"}],
            "actions": [
                {"text": "非常满意", "url": "https://example.com/survey/1", "style": "positive"},
                {"text": "满意", "url": "https://example.com/survey/2", "style": "default"},
                {"text": "不满意", "url": "https://example.com/survey/3", "style": "default"}
            ]
        }
    )
)

result = await sender.send(message, "dingtalk")
```

### Multi-platform Sending

```python
# Send to all available platforms
result = await sender.send_auto(message)

# Send to multiple specific platforms
result = await sender.send_multi(
    message,
    platforms=["wecom", "dingtalk", "feishu"]
)
```

## CLI Usage

```bash
# Send text message
webhook-push send dingtalk "https://oapi.dingtalk.com/robot/send?access_token=xxx" \
    --content "Hello from CLI!"

# Send Markdown message
webhook-push send wecom "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx" \
    --type markdown \
    --title "Report" \
    --content "# Daily Report\n- Metric 1"

# Send to multiple platforms
webhook-push send-multi wecom dingtalk --content "Notification"

# Send to all available platforms
webhook-push send-auto --content "All platforms"

# View platform info
webhook-push info dingtalk
```

## Best Practices

### 1. Use Markdown for Best Compatibility

Markdown has good support across all platforms:

```python
message = UnifiedMessage(
    content={
        "type": "markdown",
        "body": {
            "content": """# Report

## Summary
- **Key Metric**: 128
- Another metric

> Important note

[View Details](https://example.com)"""
        }
    }
)
```

### 2. Handle Failures Gracefully

```python
result = await sender.send(message, "dingtalk", webhook_url)

if not result.success:
    if result.retry_suggested:
        # Retry later
        await retry_queue.add(message)
    else:
        # Log error
        logger.error(f"Send failed: {result.error}")
```

### 3. Use Card Messages for Interaction

Card messages provide a better user experience:

```python
message = UnifiedMessage(
    content={
        "type": "card",
        "body": {
            "card_type": "interactive",
            "elements": [{"type": "div", "text": "Needs approval"}],
            "actions": [
                {"type": "button", "text": "Approve", "url": "...", "style": "primary"},
                {"type": "button", "text": "Reject", "url": "..."}
            ]
        }
    }
)
```

### 4. Monitor Rate Limits

Be aware of rate limits for each platform:

| Platform | Rate Limit |
|----------|------------|
| WeCom | 20/min |
| DingTalk | 20/min |
| Feishu | No explicit limit |

The sender automatically handles rate limit errors.

## Development

### Install Development Dependencies

```bash
poetry install
```

### Run Tests

```bash
pytest
```

### Code Quality

```bash
# Black formatting
black src/ tests/

# isort sorting
isort src/ tests/

# ruff check
ruff check src/ tests/

# mypy type checking
mypy src/
```

## Project Structure

```
webhook-push/
├── README.md                      # English documentation
├── README_CN.md                  # Chinese documentation
├── SKILL.md                      # Skill documentation
├── pyproject.toml                # Project configuration
├── references/                   # Reference documents
│   ├── api-reference.md         # API reference
│   ├── platform-docs.md         # Platform documentation links
│   ├── webhook-push-skill-design.md        # Design specification
│   └── webhook-push-unified-message-design.md # API design
├── src/webhook_push/            # Python source code
│   ├── models/                  # Data models
│   ├── adapters/                # Platform adapters
│   ├── converters/              # Message converters
│   ├── sender/                  # Sender
│   └── cli.py                   # CLI
└── tests/                       # Tests
```

## Configuration

### Environment Variables

```bash
# Enterprise WeCom
WECOM_WEBHOOK_KEY=your-webhook-key

# DingTalk
DINGTALK_ACCESS_TOKEN=your-access-token
DINGTALK_SECRET=your-signing-secret

# Feishu
FEISHU_WEBHOOK_ID=your-webhook-id
```

### Configuration File

Create a `webhook-push.yaml` file:

```yaml
platforms:
  wecom:
    webhook_url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
  dingtalk:
    webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=xxx"
    secret: "xxx"
  feishu:
    webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"

retry:
  max_retries: 3
  initial_delay: 1000
  max_delay: 30000
  backoff_multiplier: 2
```

## Message Types

| Type | WeCom | DingTalk | Feishu |
|------|-------|----------|--------|
| text | ✅ | ✅ | ✅ |
| markdown | ✅ (2 variants) | ✅ | ✅ |
| image | ✅ | ❌ | ✅ |
| link | ❌ | ✅ | ❌ |
| card | ✅ | ✅ | ✅ |
| file | ✅ | ❌ | ✅ |
| feed | news | feedCard | ❌ |

## Platform-specific Notes

### Enterprise WeCom

- Markdown messages support 2048 bytes (standard) or 4096 bytes (v2)
- Images must be base64 encoded with MD5 hash
- Text messages support @mentions via userid or mobile

### DingTalk

- Maximum 20 messages per minute per robot
- Webhook mode does not support image, file, or voice messages
- Supports signature verification (recommended)

### Feishu

- V2 webhook is recommended (more features)
- V1 webhook only supports plain text
- Rich interactive card support

## CLI Usage

```bash
# Send text message
webhook-push send dingtalk "https://oapi.dingtalk.com/robot/send?access_token=xxx" \
    --content "Hello from CLI!"

# Send Markdown message
webhook-push send wecom "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx" \
    --type markdown \
    --title "Report" \
    --content "# Daily Report\n- Metric 1"

# Send to multiple platforms
webhook-push send-multi wecom dingtalk --content "Notification"

# Send to all available platforms
webhook-push send-auto --content "All platforms"

# View platform info
webhook-push info dingtalk
```

## Best Practices

### 1. Use Markdown for Best Compatibility

Markdown has good support across all platforms:

```python
message = UnifiedMessage(
    content={
        "type": "markdown",
        "body": {
            "content": """# Report

## Summary
- **Key Metric**: 128
- Another metric

> Important note

[View Details](https://example.com)"""
        }
    }
)
```

### 2. Handle Failures Gracefully

```python
result = await sender.send(message, "dingtalk", webhook_url)

if not result.success:
    if result.retry_suggested:
        # Retry later
        await retry_queue.add(message)
    else:
        # Log error
        logger.error(f"Send failed: {result.error}")
```

### 3. Use Card Messages for Interaction

Card messages provide a better user experience:

```python
message = UnifiedMessage(
    content={
        "type": "card",
        "body": {
            "card_type": "interactive",
            "elements": [{"type": "div", "text": "Needs approval"}],
            "actions": [
                {"type": "button", "text": "Approve", "url": "...", "style": "primary"},
                {"type": "button", "text": "Reject", "url": "..."}
            ]
        }
    }
)
```

### 4. Monitor Rate Limits

Be aware of rate limits for each platform:

| Platform | Rate Limit |
|----------|------------|
| WeCom | 20/min |
| DingTalk | 20/min |
| Feishu | No explicit limit |

The sender automatically handles rate limit errors.

## Development

### Install Development Dependencies

```bash
poetry install
```

### Run Tests

```bash
pytest
```

### Code Quality

```bash
# Black formatting
black src/ tests/

# isort sorting
isort src/ tests/

# ruff check
ruff check src/ tests/

# mypy type checking
mypy src/
```

## Project Structure

```
webhook-push/
├── README.md                      # English documentation
├── README_CN.md                  # Chinese documentation
├── SKILL.md                      # Skill documentation
├── pyproject.toml                # Project configuration
├── references/                   # Reference documents
│   ├── api-reference.md         # API reference
│   ├── platform-docs.md         # Platform documentation links
│   ├── webhook-push-skill-design.md        # Design specification
│   └── webhook-push-unified-message-design.md # API design
├── src/webhook_push/            # Python source code
│   ├── models/                  # Data models
│   ├── adapters/                # Platform adapters
│   ├── converters/              # Message converters
│   ├── sender/                  # Sender
│   └── cli.py                   # CLI
└── tests/                       # Tests
```

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE.md](LICENSE.md) for details.

## Acknowledgments

- Thanks to the developers of WeCom, DingTalk, and Feishu
- Inspired by various enterprise messaging APIs
