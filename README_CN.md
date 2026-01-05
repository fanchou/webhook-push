# Webhook Push Skill - 企业消息推送工具

[![PyPI 版本](https://badge.fury.io/py/webhook-push.svg)](https://badge.fury.io/py/webhook-push)
[![Python 版本](https://img.shields.io/pypi/pyversions/webhook-push.svg)](https://pypi.org/project/webhook-push/)
[![许可证](https://img.shields.io/pypi/l/webhook-push.svg)](https://pypi.org/project/webhook-push/)

统一的消息推送工具，支持向企业微信、钉钉和飞书三大企业通讯平台发送 Webhook 消息。

## 简介

本工具提供了一个统一的接口，可以向以下三个主流企业通讯平台发送消息：

- **企业微信（WeCom）** - 腾讯推出的企业通讯工具
- **钉钉（DingTalk）** - 阿里巴巴的企业协作平台
- **飞书（Lark/Feishu）** - 字节跳动的企业协作平台

## 主要特性

- **统一消息模型** - 使用单一、平台无关的接口发送消息
- **多平台支持** - 企业微信、钉钉、飞书
- **丰富消息类型** - 文本、Markdown、图片、链接、卡片、文件、Feed
- **自动转换** - 消息自动转换为平台特定格式
- **优雅降级** - 不支持的功能自动降级
- **重试机制** - 内置指数退避重试逻辑
- **频率限制** - 平台特定的频率限制处理

## 安装

```bash
pip install webhook-push
```

## 快速开始

```python
from webhook_push import MessageSender, UnifiedMessage

# 创建文本消息
message = UnifiedMessage(
    content={
        "type": "text",
        "body": {"text": "来自 webhook-push 的消息！"}
    }
)

# 发送到指定平台
sender = MessageSender()
result = await sender.send(
    message,
    "dingtalk",
    webhook_url="https://oapi.dingtalk.com/robot/send?access_token=xxx"
)
print(result)
```

## 使用示例

### 发送文本消息

```python
from webhook_push import UnifiedMessage

message = UnifiedMessage(
    metadata={"message_id": "msg_001"},
    content={
        "type": "text",
        "title": "通知",
        "body": {"text": "这是一条测试消息"},
        "mentions": [{"type": "mobile", "value": "13800000000"}]
    }
)
```

### 发送 Markdown 消息

```python
message = UnifiedMessage(
    content={
        "type": "markdown",
        "title": "每日报告",
        "body": {
            "content": """# 每日报告

## 核心指标
- **新增用户**: 128
- *活跃用户*: 3,421

> 最后更新: 18:00"""
        }
    }
)
```

### 发送卡片消息

卡片消息提供更丰富的交互体验，支持按钮跳转。各平台支持的卡片类型不同：

#### 企业微信 - 模板卡片（文本通知）

```python
message = UnifiedMessage(
    content={
        "type": "card",
        "body": {
            "card_type": "text_notice",
            "title": "系统告警",
            "description": "CPU使用率超过阈值，请及时处理",
            "emphasis": {
                "title": "95%",
                "desc": "当前CPU使用率"
            },
            "horizontal_content_list": [
                {"keyname": "服务器", "value": "web-01"},
                {"keyname": "阈值", "value": "80%"},
                {"keyname": "告警级别", "value": "严重", "type": 2}
            ],
            "jump_list": [
                {"type": 1, "url": "https://example.com/alerts", "title": "查看详情"}
            ],
            "action": {"type": 1, "url": "https://example.com/alerts"}
        }
    }
)

result = await sender.send(message, "wecom")
```

#### 企业微信 - 模板卡片（图文展示）

```python
message = UnifiedMessage(
    content={
        "type": "card",
        "body": {
            "card_type": "news_show",
            "title": "技术分享: Webhook 最佳实践",
            "image_url": "https://example.com/cover.jpg",
            "url": "https://example.com/article",
            "main_title": {
                "title": "Webhook 最佳实践指南",
                "desc": "了解如何设计可靠的 webhook 系统"
            }
        }
    }
)

result = await sender.send(message, "wecom")
```

#### 钉钉 - 动作卡片（单个按钮）

```python
message = UnifiedMessage(
    content={
        "type": "card",
        "body": {
            "card_type": "single",
            "config": {"hide_avatar": "0"},
            "title": "审批请求",
            "elements": [
                {"type": "div", "text": "您有一个新的审批请求待处理\n\n申请人：张三\n申请时间：2024-01-05 10:30"}
            ],
            "actions": [
                {"text": "立即审批", "url": "https://example.com/approve?id=123", "style": "positive"}
            ]
        }
    }
)

result = await sender.send(message, "dingtalk")
```

#### 钉钉 - 动作卡片（多个按钮）

```python
message = UnifiedMessage(
    content={
        "type": "card",
        "body": {
            "card_type": "multi",
            "config": {"hide_avatar": "0", "btn_orientation": "1"},
            "title": "满意度调查",
            "elements": [
                {"type": "div", "text": "请对本次服务进行评价，您的反馈对我们非常重要"}
            ],
            "actions": [
                {"text": "非常满意", "url": "https://example.com/survey/1", "style": "positive"},
                {"text": "满意", "url": "https://example.com/survey/2", "style": "default"},
                {"text": "不满意", "url": "https://example.com/survey/3", "style": "default"}
            ]
        }
    }
)

result = await sender.send(message, "dingtalk")
```

#### 飞书 - 交互卡片

```python
message = UnifiedMessage(
    content={
        "type": "card",
        "body": {
            "config": {
                "wide_screen_mode": True,
                "enable_forward": True
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": "**审批提醒**\n您有一个新的待审批事项"}
                }
            ],
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "立即审批"},
                    "url": "https://example.com/approve",
                    "type": "primary"
                }
            ]
        }
    }
)

result = await sender.send(message, "feishu")
```

### 多平台发送

```python
# 发送到所有可用平台
result = await sender.send_auto(message)
print(f"成功发送到: {result.sent_platforms}")

# 发送到多个指定平台
result = await sender.send_multi(
    message,
    platforms=["wecom", "dingtalk", "feishu"]
)
```

## 配置

### 环境变量（可选）

```bash
# 企业微信
WECOM_WEBHOOK_KEY=your-webhook-key

# 钉钉
DINGTALK_ACCESS_TOKEN=your-access-token
DINGTALK_SECRET=your-signing-secret

# 飞书
FEISHU_WEBHOOK_ID=your-webhook-id
```

### 配置文件

创建 `webhook-push.yaml` 文件：

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

## 支持的消息类型

| 类型 | 企业微信 | 钉钉 | 飞书 |
|------|---------|------|------|
| text | ✅ | ✅ | ✅ |
| markdown | ✅（2种） | ✅ | ✅ |
| image | ✅ | ❌ | ✅ |
| link | ❌ | ✅ | ❌ |
| card | ✅ | ✅ | ✅ |
| file | ✅ | ❌ | ✅ |
| feed | news | feedCard | ❌ |

## 平台说明

### 企业微信

- Markdown 消息支持 2048 字节（标准）或 4096 字节（V2）
- 图片必须经过 Base64 编码并提供 MD5 哈希
- 文本消息支持通过 userid 或手机号 @提及成员

### 钉钉

- 每个机器人每分钟最多发送 20 条消息
- Webhook 模式不支持图片、文件或语音消息
- 建议启用签名验证

### 飞书

- 推荐使用 V2 Webhook（功能更丰富）
- V1 Webhook 仅支持纯文本
- 支持丰富的交互卡片

## CLI 使用

```bash
# 发送文本消息
webhook-push send dingtalk "https://oapi.dingtalk.com/robot/send?access_token=xxx" \
    --content "Hello from CLI!"

# 发送 Markdown 消息
webhook-push send wecom "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx" \
    --type markdown \
    --title "报告" \
    --content "# 每日报告\n- 指标1"

# 发送到多个平台
webhook-push send-multi wecom dingtalk --content "通知"

# 发送到所有可用平台
webhook-push send-auto --content "所有平台"

# 查看平台信息
webhook-push info dingtalk
```

## 最佳实践

### 1. 使用 Markdown 获得最佳兼容性

Markdown 在各平台都有良好的支持：

```python
message = UnifiedMessage(
    content={
        "type": "markdown",
        "body": {
            "content": """# 报告

## 摘要
- **关键指标**: 128
- 另一个指标

> 重要提示

[查看详情](https://example.com)"""
        }
    }
)
```

### 2. 优雅处理失败

```python
result = await sender.send(message, "dingtalk", webhook_url)

if not result.success:
    if result.retry_suggested:
        # 稍后重试
        await retry_queue.add(message)
    else:
        # 记录错误
        logger.error(f"发送失败: {result.error}")
```

### 3. 使用卡片消息进行交互

卡片消息提供更好的用户体验：

```python
message = UnifiedMessage(
    content={
        "type": "card",
        "body": {
            "card_type": "interactive",
            "elements": [{"type": "div", "text": "需要审批"}],
            "actions": [
                {"type": "button", "text": "通过", "url": "...", "style": "primary"},
                {"type": "button", "text": "拒绝", "url": "..."}
            ]
        }
    }
)
```

### 4. 监控频率限制

注意各平台的频率限制：

| 平台 | 频率限制 |
|------|---------|
| 企业微信 | 20/分钟 |
| 钉钉 | 20/分钟 |
| 飞书 | 无明确限制 |

发送器会自动处理频率限制错误。

## 开发

### 安装开发依赖

```bash
poetry install
```

### 运行测试

```bash
pytest
```

### 代码检查

```bash
# Black 格式化
black src/ tests/

# isort 排序
isort src/ tests/

# ruff 检查
ruff check src/ tests/

# mypy 类型检查
mypy src/
```

## 项目结构

```
webhook-push/
├── README.md                      # 英文说明
├── README_CN.md                  # 中文说明（本文档）
├── SKILL.md                      # Skill 文档
├── pyproject.toml                # 项目配置
├── references/                   # 参考文档
│   ├── api-reference.md         # API 参考
│   ├── platform-docs.md         # 平台文档链接
│   ├── webhook-push-skill-design.md        # 设计规范
│   └── webhook-push-unified-message-design.md # API 设计
├── src/webhook_push/            # Python 源码
│   ├── models/                  # 数据模型
│   ├── adapters/                # 平台适配器
│   ├── converters/              # 消息转换器
│   ├── sender/                  # 发送器
│   └── cli.py                   # CLI
└── tests/                       # 测试
```

## 贡献

欢迎贡献！请阅读 [CONTRIBUTING.md](docs/CONTRIBUTING.md) 了解贡献指南。

## 许可证

MIT 许可证 - 请查看 [LICENSE.md](LICENSE.md) 了解更多详情。

## 致谢

- 感谢企业微信、钉钉和飞书的开发者
- 借鉴了各种企业消息 API 的设计
