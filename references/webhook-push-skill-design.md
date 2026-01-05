# Webhook Push Skill 设计文档

## 1. 概述

### 1.1 目的与范围

本文档描述了 `webhook-push` 技能的详细设计方案。该技能旨在为 AI 助手提供一个统一的接口，通过 Webhook 方式向三大企业通讯平台发送消息：企业微信、钉钉和飞书。

**核心目标**：
- 提供简洁统一的 API，屏蔽不同平台的差异性
- 支持多种消息类型：文本、Markdown、图片、文件、卡片等
- 实现健壮的错误处理和重试机制
- 确保消息送达的可靠性
- 为未来扩展其他平台预留扩展点

### 1.2 支持平台

| 平台 | 官方名称 | Webhook 类型 | 主要特性 |
|------|----------|--------------|----------|
| 企业微信 | WeCom | 群机器人 V1 | 支持 Markdown_v2、模板卡片、语音、文件 |
| 钉钉 | DingTalk | 群机器人 V1 | 支持 Markdown、加签验证、FeedCard |
| 飞书 | Feishu/Lark | 自定义机器人 V1/V2 | 支持富文本、交互式卡片、V1 纯文本兼容 |

### 1.3 核心功能特性

**消息发送**：
- 单条消息发送
- 批量消息发送（支持不同平台）
- 同步/异步发送模式

**消息类型**：
- 纯文本消息
- Markdown 消息（各平台语法略有差异）
- 图片消息（支持 URL 和 Base64）
- 文件消息（需先上传获取 Media ID）
- 富文本卡片
- 按钮交互卡片
- 语音消息（企业微信、飞书）
- 图文消息（企业微信）
- FeedCard 消息（钉钉）

**可靠性保障**：
- 自动重试机制（指数退避）
- 失败消息记录
- 详细的错误分类

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Webhook Push Skill                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐   ┌──────────────┐   ┌─────────────────────┐   │
│  │   Unified   │──▶│   Message    │──▶│   Platform Adapter  │   │
│  │   Interface │   │  Formatter   │   │     Layer           │   │
│  └─────────────┘   └──────────────┘   └─────────────────────┘   │
│                                                 │                │
│                                                 ▼                │
│  ┌─────────────┐   ┌──────────────┐   ┌─────────────────────┐   │
│  │   Config   │◀──│   Error      │◀──│   Network Layer     │   │
│  │  Manager   │   │  Handler     │   │                     │   │
│  └─────────────┘   └──────────────┘   └─────────────────────┘   │
│                                                 │                │
│           ┌────────────────────────────────────┘                │
│           ▼                                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                  Platform Adapters                       │    │
│  ├──────────────┬──────────────┬──────────────────────────┤    │
│  │   WeCom     │   DingTalk   │         Feishu           │    │
│  │  Adapter    │   Adapter    │         Adapter           │    │
│  └──────────────┴──────────────┴──────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 核心组件

#### 2.2.1 Unified Interface（统一接口层）

作为技能的对外入口，负责：
- 接收标准化的消息请求
- 验证输入参数
- 路由到对应的平台适配器
- 返回统一格式的响应

#### 2.2.2 Message Formatter（消息格式化器）

负责将统一消息格式转换为平台特定的消息格式：
- Markdown 语法转换（各平台语法差异处理）
- 特殊内容格式转换
- 字符编码处理
- 长度截断与优化

#### 2.2.3 Platform Adapter Layer（平台适配器层）

每个平台对应一个独立的适配器，负责：
- 平台特定的 HTTP 请求构建
- Webhook URL 管理
- 平台特有的消息类型支持
- 平台错误码映射

#### 2.2.4 Network Layer（网络层）

负责底层的 HTTP 通信：
- 请求发送与响应处理
- 超时控制
- 重试逻辑
- SSL/TLS 处理

#### 2.2.5 Error Handler（错误处理器）

负责统一的错误处理：
- 错误分类与编码
- 重试决策
- 错误日志记录
- 用户友好的错误消息

#### 2.2.6 Config Manager（配置管理器）

负责运行时配置管理：
- Webhook URL 管理
- 平台凭证管理（部分平台需要）
- 重试策略配置
- 限流配置

### 2.3 数据流程

```
用户请求 ──▶ 统一接口 ──▶ 参数验证 ──▶ 消息格式化
                                            │
                                            ▼
                                     平台适配器 ──▶ HTTP 请求
                                            │
                                            ▼
                                     响应处理 ──▶ 错误判断
                                            │
                          ┌─────────────────┼─────────────────┐
                          ▼                 ▼                 ▼
                      成功返回           重试队列          错误记录
```

---

## 3. 平台特定实现

### 3.1 企业微信（WeCom）

#### 3.1.1 Webhook URL 格式

```
https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={WEBHOOK_KEY}
```

**配置要求**：
- Webhook Key：长度为 43-120 字符的字符串
- 每个群机器人对应一个唯一的 Webhook Key
- Key 需要在群聊设置中获取

#### 3.1.2 消息负载结构

**文本消息**：
```json
{
  "msgtype": "text",
  "text": {
    "content": "消息内容",
    "mentioned_list": ["userid1", "userid2"],
    "mentioned_mobile_list": ["13800000000", "@all"]
  }
}
```

**Markdown 消息**：
```json
{
  "msgtype": "markdown",
  "markdown": {
    "content": "**标题**\n> 引用内容\n- 列表项1\n- 列表项2"
  }
}
```

**图片消息**：
```json
{
  "msgtype": "image",
  "image": {
    "base64": "图片Base64编码",
    "md5": "图片MD5校验值"
  }
}
```

#### 3.1.3 支持的消息类型

| 消息类型 | 支持状态 | 备注 |
|---------|---------|------|
| text | ✅ 支持 | 支持@用户 |
| markdown | ✅ 支持 | 标准 Markdown，支持字体颜色 |
| markdown_v2 | ✅ 支持 | 增强版 Markdown，支持表格/斜体等 |
| image | ✅ 支持 | 需要 Base64 + MD5，最大 2MB |
| news | ✅ 支持 | 图文消息（1-8 条） |
| file | ✅ 支持 | 需要先上传获取 media_id |
| voice | ✅ 支持 | 需要先上传获取 media_id |
| template_card | ✅ 支持 | 模板卡片（文本通知/图文展示） |

#### 3.1.4 Markdown 语法详解

##### 标准 Markdown（markdown 类型）

企业微信标准 Markdown 支持以下语法：

```markdown
# 标题一（一级标题，注意#与文字中间要有空格）
## 标题二
### 标题三
#### 标题四
##### 标题五
###### 标题六

**加粗**

[这是一个链接](https://work.weixin.qq.com/api/doc)

`行内代码`

> 引用文字

<font color="info">绿色</font>
<font color="comment">灰色</font>
<font color="</font>

warning">橙红色支持通过 <@userid> 或 <@all> @群成员
```

##### 增强版 Markdown（markdown_v2 类型）

markdown_v2 是新版本 Markdown 语法，支持更丰富的格式，但**不支持字体颜色和@群成员**：

```markdown
# 标题一
## 二级标题
### 三级标题

*斜体*
**加粗**

- 无序列表 1
- 无序列表 2
  - 无序列表 2.1
  - 无序列表 2.2
1. 有序列表 1
2. 有序列表 2

> 一级引用
>> 二级引用
>>> 三级引用

[这是一个链接](https://work.weixin.qq.com/api/doc)
![图片描述](https://res.mail.qq.com/node/ww/wwopenmng/images/test.png)

---

`行内代码`
```
多行代码块
```

| 姓名 | 文化衫尺寸 | 收货地址 |
| :----- | :----: | -------: |
| 张三 | S | 广州 |
| 李四 | L | 深圳 |
```

**注意**：markdown_v2 在客户端 4.1.36 版本以下（安卓端为 4.1.38 以下）会表现为纯文本，建议使用最新客户端版本。

#### 3.1.5 模板卡片（template_card）

##### 文本通知模板卡片（text_notice）

```json
{
  "msgtype": "template_card",
  "template_card": {
    "card_type": "text_notice",
    "source": {
      "icon_url": "https://example.com/icon.png",
      "desc": "来源名称",
      "desc_color": 0
    },
    "main_title": {
      "title": "主标题",
      "desc": "主标题描述"
    },
    "emphasis_content": {
      "title": "强调内容标题",
      "desc": "强调内容描述"
    },
    "quote_area": {
      "type": 1,
      "url": "https://example.com",
      "title": "引用区域标题",
      "quote_text": "引用文本内容"
    },
    "sub_title_text": "副标题文字",
    "horizontal_content_list": [
      {
        "keyname": "关键字1",
        "value": "值1"
      },
      {
        "keyname": "关键字2",
        "value": "点击访问",
        "type": 1,
        "url": "https://example.com"
      }
    ],
    "jump_list": [
      {
        "type": 1,
        "url": "https://example.com",
        "title": "跳转按钮1"
      }
    ],
    "card_action": {
      "type": 1,
      "url": "https://example.com",
      "title": "卡片点击"
    }
  }
}
```

##### 图文展示模板卡片（news_show）

```json
{
  "msgtype": "template_card",
  "template_card": {
    "card_type": "news_show",
    "source": {
      "icon_url": "https://example.com/icon.png",
      "desc": "来源"
    },
    "main_title": {
      "title": "卡片标题",
      "desc": "卡片描述"
    },
    "card_image": {
      "url": "https://example.com/image.png",
      "aspect_ratio": 1.0
    },
    "image_area": {
      "type": "1",
      "url": "https://example.com/detail.png"
    },
    "quote_area": {
      "type": 2,
      "url": "https://example.com",
      "title": "引用标题",
      "quote_text": "引用文本"
    },
    "horizontal_content_list": [
      {
        "keyname": "关键词",
        "value": "值"
      }
    ],
    "jump_list": [
      {
        "type": 1,
        "url": "https://example.com",
        "title": "跳转"
      }
    ]
  }
}
```

#### 3.1.6 限制与配额

| 限制项 | 数值 | 说明 |
|-------|------|------|
| 消息频率 | 20条/分钟 | 超过限制返回错误 |
| Markdown 内容 | 2048字节 | markdown 类型 |
| Markdown_v2 内容 | 4096字节 | markdown_v2 类型 |
| 图片大小 | 2MB | Base64 编码前，支持 JPG、PNG |
| 图文标题 | 128字节 | 超过自动截断 |
| 图文描述 | 512字节 | 超过自动截断 |
| 图文数量 | 1-8条 | news 类型 |
| 文件/语音 | - | 需要通过上传接口获取 media_id |

#### 3.1.7 错误码处理

| 错误码 | 含义 | 处理建议 |
|-------|------|---------|
| 0 | 成功 | - |
| -1 | 系统繁忙 | 稍后重试 |
| 40001 | 获取 access_token 失败 | 检查凭证配置 |
| 40014 | access_token 无效 | 刷新 token |
| 41004 | 缺少 access_token 参数 | 检查请求参数 |
| 60004 | Webhook Key 无效 | 检查 Key 配置 |
| 60020 | IP 不在白名单 | 需配置 IP 白名单 |
| 60009 | 内容包含敏感词 | 修改消息内容 |
| 60008 | 请求过于频繁 | 实施限流重试 |

#### 3.1.8 安全注意事项

> **⚠️ 重要**：一定要**保护好消息推送的 Webhook 地址**，避免泄漏！不要分享到 GitHub、博客等可被公开查阅的地方，否则坏人就可以用你的消息推送来发垃圾消息。

**安全建议**：
1. Webhook URL 存储在环境变量或加密配置中
2. 对外只提供发送消息的封装接口，不暴露原始 URL
3. 定期更换 Webhook Key
4. 配置 IP 白名单限制访问来源
5. 监控异常发送行为

---

### 3.2 钉钉（DingTalk）

#### 3.2.1 Webhook URL 格式

```
https://oapi.dingtalk.com/robot/send?access_token={ACCESS_TOKEN}
```

**配置要求**：
- Access Token：从自定义机器人的 Webhook URL 中获取
- Webhook URL 格式：`https://oapi.dingtalk.com/robot/send?access_token=xxx`
- 每个群机器人对应一个唯一的 access_token
- 机器人需要在钉钉群聊中添加

**获取方式**：
1. 打开钉钉群聊设置
2. 点击"智能群助手"
3. 添加"自定义机器人"
4. 复制 Webhook URL（包含 access_token）

**安全设置**：
钉钉支持以下安全配置（可在机器人设置中启用）：
- **自定义关键词**：消息中必须包含的关键词
- **加签**：基于时间戳和密钥的签名验证
- **IP 白名单**：限制可访问的 IP 地址范围

#### 3.2.2 消息负载结构

**文本消息**：
```json
{
  "msgtype": "text",
  "text": {
    "content": "消息内容"
  },
  "at": {
    "atMobiles": ["13800000000", "13900000000"],
    "atUserIds": ["user123", "user456"],
    "isAtAll": false
  }
}
```

**Markdown 消息**：
```json
{
  "msgtype": "markdown",
  "markdown": {
    "title": "消息标题（会在聊天列表显示）",
    "text": "# 一级标题\n## 二级标题\n> 引用内容\n- 列表项1\n- 列表项2\n[链接文字](https://dingtalk.com)"
  }
}
```

**链接消息**：
```json
{
  "msgtype": "link",
  "link": {
    "title": "链接标题",
    "text": "链接描述内容",
    "picUrl": "https://example.com/image.jpg",
    "messageUrl": "https://example.com/link"
  }
}
```

**ActionCard 消息（单按钮）**：
```json
{
  "msgtype": "actionCard",
  "actionCard": {
    "title": "卡片标题",
    "text": "卡片内容，支持 Markdown 格式\n![图片](https://example.com/image.png)",
    "hideAvatar": "0",
    "btnOrientation": "0",
    "singleTitle": "查看详情",
    "singleURL": "https://example.com/detail"
  }
}
```

**ActionCard 消息（多按钮）**：
```json
{
  "msgtype": "actionCard",
  "actionCard": {
    "title": "卡片标题",
    "text": "卡片内容，支持 Markdown 格式",
    "hideAvatar": "0",
    "btnOrientation": "1",
    "btns": [
      {
        "title": "按钮1",
        "actionURL": "https://example.com/button1"
      },
      {
        "title": "按钮2",
        "actionURL": "https://example.com/button2"
      }
    ]
  }
}
```

**FeedCard 消息（图文链接组）**：
```json
{
  "msgtype": "feedCard",
  "feedCard": {
    "links": [
      {
        "title": "文章标题1",
        "messageURL": "https://example.com/article1",
        "picURL": "https://example.com/image1.png"
      },
      {
        "title": "文章标题2",
        "messageURL": "https://example.com/article2",
        "picURL": "https://example.com/image2.png"
      },
      {
        "title": "文章标题3",
        "messageURL": "https://example.com/article3",
        "picURL": "https://example.com/image3.png"
      }
    ]
  }
}
```

**消息去重（msgUuid）**：
```json
{
  "msgtype": "text",
  "msgUuid": "唯一消息ID",  // 用于消息去重和幂等控制
  "text": {
    "content": "消息内容"
  }
}
```

#### 3.2.3 支持的消息类型

| 消息类型 | 支持状态 | 备注 |
|---------|---------|------|
| text | ✅ 支持 | 支持@提及（手机号、userId、@all） |
| markdown | ✅ 支持 | 标题必填，支持 GFM 语法 |
| link | ✅ 支持 | 链接卡片消息 |
| actionCard | ✅ 支持 | 互动卡片，支持单/多按钮 |
| feedCard | ✅ 支持 | 图文链接组（1-4 条） |
| image | ❌ 不支持 | Webhook 方式不支持 |
| file | ❌ 不支持 | Webhook 方式不支持 |
| voice | ❌ 不支持 | Webhook 方式不支持 |
| video | ❌ 不支持 | Webhook 方式不支持 |

**注意**：图片、文件、语音、视频等消息类型需要通过**接口发送**方式（使用应用 access_token），而非 Webhook 方式。

#### 3.2.4 钉钉 Markdown 语法

钉钉 Markdown 基于 GFM（GitHub Flavored Markdown）标准，支持以下语法：

**标题**：
```markdown
# 一级标题
## 二级标题
### 三级标题
#### 四级标题
##### 五级标题
###### 六级标题
```

**文本样式**：
```markdown
**加粗文字**
*斜体文字*
***加粗斜体***
~~删除线~~
`行内代码`
```

**列表**：
```markdown
- 无序列表项
- 无序列表项
  - 子列表项

1. 有序列表项
2. 有序列表项
```

**引用**：
```markdown
> 引用内容
> 多行引用
>> 二级引用
```

**链接和图片**：
```markdown
[链接文字](https://example.com)
![图片描述](https://example.com/image.png)
```

**表格**：
```markdown
| 表头1 | 表头2 | 表头3 |
|------|------|------|
| 内容1 | 内容2 | 内容3 |
| 内容4 | 内容5 | 内容6 |
```

**不支持的语法**：
- HTML 标签
- 任务列表（`- [ ] 任务`）
- 代码块（\`\`\`code\`\`\`）
- 水平分割线（`---`）

#### 3.2.5 加签安全机制（推荐启用）

加签是钉钉提供的安全验证机制，可以防止请求被篡改。

**启用步骤**：
1. 在机器人设置中启用"加签"安全设置
2. 获取签名密钥（Secret）
3. 在请求时生成签名

**签名算法**：
```python
import time
import hmac
import hashlib
import base64

timestamp = str(int(time.time() * 1000))
secret = "your-secret-key"

# 1. 构造签名字符串
string_to_sign = f"{timestamp}\n{secret}"

# 2. 使用 HMAC-SHA256 计算签名
signature = base64.b64encode(
    hmac.new(
        secret.encode('utf-8'),
        string_to_sign.encode('utf-8'),
        digestmod=hashlib.sha256
    ).digest()
).decode('utf-8')

# 3. 添加到请求头
headers = {
    "Timestamp": timestamp,
    "Sign": signature
}
```

**完整请求示例**：
```bash
curl -X POST \
  "https://oapi.dingtalk.com/robot/send?access_token=xxx" \
  -H "Content-Type: application/json" \
  -H "Timestamp: 1704067200000" \
  -H "Sign: xxxxxxxxxxxxxxxxxxxxx" \
  -d '{
    "msgtype": "text",
    "text": {
      "content": "测试消息"
    }
  }'
```

#### 3.2.6 限制与配额

| 限制项 | 数值 | 说明 |
|-------|------|------|
| 消息频率 | 20条/分钟 | 每个机器人，超限后限流 10 分钟 |
| FeedCard 数量 | 1-4条 | 图文链接数量限制 |
| Markdown 标题 | 无明确限制 | 建议不超过 64 字符 |
| Markdown 内容 | 无明确限制 | 建议不超过 5000 字符 |
| 单个链接标题 | 无明确限制 | 建议不超过 100 字符 |
| 按钮数量 | 无明确限制 | 建议不超过 5 个 |

**频率限制说明**：
- 超过 20 条/分钟后，机器人将被限流 10 分钟
- 限流期间发送的消息会返回错误
- 建议实现指数退避重试机制

#### 3.2.7 错误码处理

| 错误码 | 含义 | 处理建议 |
|-------|------|---------|
| 0 | 成功 | - |
| -1 | 系统繁忙 | 稍后重试 |
| 40001 | 获取 access_token 失败 | 检查 access_token |
| 40014 | access_token 无效 | 刷新 access_token |
| 41004 | 缺少 access_token | 检查请求参数 |
| 30001 | 机器人消息频率超限 | 降级发送，等待 10 分钟后重试 |
| 30002 | 机器人被禁言 | 检查机器人状态 |
| 30003 | 超过群成员限制 | 无法发送 |
| 30004 | 消息内容包含敏感词 | 修改内容 |
| 30100 | 参数不完整 | 检查请求参数 |
| 30109 | 图片上传失败 | 检查图片 URL |

#### 3.2.8 安全注意事项

> **⚠️ 重要**：保护好机器人的 Webhook URL 和签名密钥，避免泄漏！

**安全建议**：
1. **不要将 Webhook URL 提交到公开仓库**（GitHub、GitLab 等）
2. **启用加签验证**：防止请求被篡改
3. **设置 IP 白名单**：限制可访问的服务器 IP
4. **设置自定义关键词**：确保消息包含指定关键词
5. **定期更换签名密钥**：提高安全性
6. **监控异常发送**：及时发现恶意使用

#### 3.2.9 消息发送方式对比

钉钉机器人支持两种消息发送方式：

| 方式 | Webhook 方式 | 接口方式 |
|-----|-------------|----------|
| 端点 | `/robot/send?access_token=` | `/im/v1/messages/` |
| 认证 | 机器人 access_token | 应用 access_token |
| 消息类型 | text, markdown, link, actionCard, feedCard | text, markdown, link, image, actionCard, audio, file, video |
| 适用场景 | 简单通知、集成第三方服务 | 需要更多消息类型、功能更丰富 |

---

### 3.3 飞书（Lark/Feishu）

#### 3.3.1 Webhook URL 格式

飞书自定义机器人支持 V1 和 V2 两个版本的 Webhook：

**V2 Webhook（推荐）**：
```
https://open.feishu.cn/open-apis/bot/v2/hook/{WEBHOOK_ID}
```

**V1 Webhook（已废弃，仅支持纯文本）**：
```
https://open.feishu.cn/open-apis/bot/hook/{WEBHOOK_ID}
```

**配置要求**：
- Webhook ID：在飞书群聊中添加自定义机器人后获取
- 支持签名验证（可选）：配置签名密钥增强安全性
- 不占用应用 API 调用配额

#### 3.3.2 消息负载结构

**V2 文本消息**：
```json
{
  "msg_type": "text",
  "content": {
    "text": "消息内容"
  }
}
```

**V1 文本消息（仅支持纯文本）**：
```json
{
  "title": "可选标题",
  "text": "消息内容"
}
```

**富文本消息（post）**：
```json
{
  "msg_type": "post",
  "content": {
    "post": {
      "zh_cn": {
        "title": "帖子标题",
        "content": [
          [
            {
              "type": "text",
              "text": "第一段文本"
            },
            {
              "type": "text",
              "text": "链接文本",
              "href": "https://example.com"
            }
          ],
          [
            {
              "type": "at",
              "user_id": "ou_xxx"
            }
          ]
        ]
      }
    }
  }
}
```

**图片消息**：
```json
{
  "msg_type": "image",
  "content": {
    "image_key": "img_v2_xxx"
  }
}
```
注意：图片需要先通过上传接口获取 image_key。

**卡片消息（可交互）**：
```json
{
  "msg_type": "card",
  "content": {
    "config": {
      "wide_screen_mode": true
    },
    "header": {
      "template": "green",
      "title": {
        "content": "卡片标题",
        "tag": "plain_text"
      }
    },
    "elements": [
      {
        "tag": "div",
        "text": {
          "content": "卡片内容",
          "tag": "lark_md"
        }
      },
      {
        "tag": "action",
        "actions": [
          {
            "tag": "button",
            "text": {
              "content": "点击按钮",
              "tag": "plain_text"
            },
            "type": "primary",
            "value": {"action": "click"}
          }
        ]
      }
    ]
  }
}
```

#### 3.3.3 支持的消息类型

| 消息类型 | V2 Webhook | V1 Webhook | 备注 |
|---------|-----------|-----------|------|
| text | ✅ 支持 | ✅ 支持（仅纯文本） | 纯文本消息 |
| post | ✅ 支持 | ❌ 不支持 | 富文本消息 |
| image | ✅ 支持 | ❌ 不支持 | 需先上传获取 image_key |
| file | ✅ 支持 | ❌ 不支持 | 需先上传获取 file_key |
| audio | ✅ 支持 | ❌ 不支持 | 需先上传 |
| card | ✅ 支持 | ❌ 不支持 | 可交互卡片 |
| share_chat | ✅ 支持 | ❌ 不支持 | 分享群聊 |
| share_user | ✅ 支持 | ❌ 不支持 | 分享用户 |

#### 3.3.4 富文本（post）消息详解

飞书富文本消息支持多语言和复杂结构：

```json
{
  "msg_type": "post",
  "content": {
    "post": {
      "zh_cn": {
        "title": "中文标题",
        "content": [
          [
            {"type": "text", "text": "普通文本"},
            {"type": "lark_md", "text": "**Markdown** 文本"},
            {"type": "at", "user_id": "ou_123", "user_name": "张三"},
            {"type": "url", "url": "https://example.com", "text": "链接文本"},
            {"type": "emotion", "emotion_type": 1}
          ]
        ]
      },
      "en_us": {
        "title": "English Title",
        "content": [...]
      }
    }
  }
}
```

支持的元素类型：
- `text`：纯文本
- `lark_md`：Markdown 格式（支持加粗、斜体、链接等）
- `at`：@提及用户
- `url`：链接
- `image`：图片
- `emotion`：表情

#### 3.3.5 卡片消息详解

飞书支持丰富的卡片组件：

**卡片配置**：
```json
{
  "config": {
    "wide_screen_mode": true,    // 宽屏模式
    "enable_forward": true       // 允许转发
  }
}
```

**卡片组件**：
- `div`：文本区块
- `img`：图片
- `hr`：分割线
- `note`：备注
- `action`：交互区域
- `button`：按钮
- `select`：下拉选择
- `date_picker`：日期选择

**按钮类型**：
- `default`：默认按钮
- `primary`：主要按钮（蓝色）
- `danger`：危险按钮（红色）

#### 3.3.6 限制与配额

| 限制项 | 数值 | 说明 |
|-------|------|------|
| 消息频率 | 无明确限制 | 建议控制在合理范围内 |
| V1 Webhook | 仅支持纯文本 | 已废弃，建议使用 V2 |
| 消息大小 | 无明确限制 | 建议不超过 30KB |
| 图片大小 | 10MB | 支持 JPG、PNG、GIF |
| 文件大小 | 100MB | 支持所有常见格式 |
| 卡片元素 | 50个 | 单个卡片最多元素 |
| Markdown 长度 | 无明确限制 | - |
| 标题长度 | 无明确限制 | - |

**重要说明**：
- 自定义机器人 Webhook 推送**不占用**应用的 API 调用配额
- 卡片消息在移动端显示效果更佳
- 建议使用 V2 Webhook，V1 仅作为兼容保留

#### 3.3.7 错误码处理

| 错误码 | 含义 | 处理建议 |
|-------|------|---------|
| 0 | 成功 | - |
| 216100 | 消息内容过长 | 截断或分片 |
| 216401 | Webhook Key 不存在 | 检查 Webhook ID |
| 216403 | 无发送权限 | 检查机器人配置 |
| 216429 | 请求过于频繁 | 降级发送，重试 |
| 216500 | 无效的 JSON | 检查请求格式 |
| 216613 | 消息类型不支持 | 使用支持的消息类型 |
| 216629 | 消息频率超限 | 降级发送，重试 |

#### 3.3.8 安全配置

飞书支持签名验证增强安全性：

1. 在飞书后台启用签名验证并获取签名密钥
2. 在请求头中添加签名：
   ```
   X-Lark-Signature: {HMAC-SHA256 签名}
   Timestamp: {时间戳}
   ```

**签名算法**：
```
signature = HMAC-SHA256(timestamp + "\n" + secret, timestamp + "\n" + body)
```

#### 3.3.9 与飞书应用的区分

**自定义机器人**：
- 通过群聊添加，无需开发应用
- 通过 Webhook URL 发送消息
- 不占用 API 调用配额
- 功能相对简单

**飞书应用消息**：
- 需要创建飞书应用
- 通过 OpenAPI 发送消息
- 占用 API 调用配额
- 功能更丰富，支持更多场景

---

## 4. API 设计

### 4.1 工具函数定义

#### 4.1.1 send_webhook_message

发送一条 Webhook 消息到指定平台。

**工具名称**：`send_webhook_message`

**输入参数**：
```typescript
{
  platform: "wecom" | "dingtalk" | "feishu",
  webhook_url: string,
  message_type: "text" | "markdown" | "markdown_v2" | "image" | "link" | "card" | "file" | "voice" | "news",
  content: {
    // 通用字段
    text?: string,           // 文本内容
    
    // Markdown 相关
    title?: string,          // 标题（部分平台需要）
    markdown_version?: "standard" | "v2",  // Markdown 版本（仅企业微信）
    
    // 图片相关
    image_url?: string,      // 图片 URL
    image_base64?: string,   // Base64 编码
    image_md5?: string,      // MD5 校验值（部分平台需要）
    
    // 链接相关
    link_url?: string,       // 链接地址
    link_title?: string,     // 链接标题
    link_text?: string,      // 链接描述
    link_image_url?: string, // 链接配图
    
    // 卡片相关
    card_config?: object,    // 卡片配置
    card_elements?: object[], // 卡片元素
    card_actions?: object[],  // 卡片交互
    
    // 高级配置
    at_users?: string[],     // @用户列表
    at_all?: boolean,        // @全体成员
  },
  options?: {
    timeout?: number,        // 超时时间（毫秒）
    retry_count?: number,    // 重试次数
    retry_interval?: number, // 重试间隔（毫秒）
    async_mode?: boolean,    // 异步模式
  }
}
```

**输出格式**：
```typescript
{
  success: boolean,
  platform: string,
  message_id?: string,      // 平台返回的消息 ID
  error?: {
    code: string,
    message: string,
    details?: object
  },
  retry_suggested?: boolean, // 是否建议重试
  metadata?: {
    sent_at: string,
    response_time: number,
    platform_response?: object
  }
}
```

**错误码定义**：

| 错误码 | 说明 | 处理建议 |
|-------|------|---------|
| WHP001 | 无效的 Webhook URL | 检查 URL 格式 |
| WHP002 | 消息类型不支持 | 使用支持的消息类型 |
| WHP003 | 内容格式错误 | 修复消息格式 |
| WHP004 | 网络超时 | 可以重试 |
| WHP005 | 平台 API 错误 | 根据具体错误处理 |
| WHP006 | 超过频率限制 | 实施限流后重试 |
| WHP007 | 内容包含敏感词 | 修改消息内容 |
| WHP008 | 平台凭证无效 | 检查配置 |
| WHP009 | 消息过长 | 截断或分片 |
| WHP010 | 文件大小超限 | 压缩或分片 |

#### 4.1.2 send_batch_webhook_messages

批量发送 Webhook 消息。

**工具名称**：`send_batch_webhook_messages`

**输入参数**：
```typescript
{
  messages: Array<{
    platform: "wecom" | "dingtalk" | "feishu",
    webhook_url: string,
    message_type: string,
    content: object,
  }>,
  options?: {
    concurrency?: number,    // 并发数（默认 5）
    continue_on_error?: boolean, // 错误时继续
    timeout?: number,        // 单条超时
  }
}
```

**输出格式**：
```typescript
{
  total: number,
  success_count: number,
  failed_count: number,
  results: Array<{
    index: number,
    success: boolean,
    message_id?: string,
    error?: object
  }>
}
```

#### 4.1.3 verify_webhook_url

验证 Webhook URL 的有效性。

**工具名称**：`verify_webhook_url`

**输入参数**：
```typescript
{
  platform: "wecom" | "dingtalk" | "feishu",
  webhook_url: string,
}
```

**输出格式**：
```typescript
{
  valid: boolean,
  platform: string,
  details?: {
    is_active: boolean,
    rate_limit_info?: object,
    permissions?: string[]
  },
  error?: object
}
```

#### 4.1.4 format_markdown_for_platform

将 Markdown 转换为平台特定格式。

**工具名称**：`format_markdown_for_platform`

**输入参数**：
```typescript
{
  source_markdown: string,
  target_platform: "wecom" | "dingtalk" | "feishu",
  options?: {
    truncate_length?: number,    // 最大长度
    convert_links?: boolean,     // 转换链接格式
    escape_special_chars?: boolean, // 转义特殊字符
  }
}
```

**输出格式**：
```typescript
{
  formatted_content: string,
  platform: string,
  warnings?: string[],      // 格式警告
  truncated: boolean,       // 是否被截断
  original_length: number,
  formatted_length: number
}
```

### 4.2 平台映射表

#### 4.2.1 消息类型映射

| 统一类型 | 企业微信 | 钉钉 | 飞书 |
|---------|---------|------|------|
| text | text | text | text |
| markdown | markdown / markdown_v2 | markdown | post（通过 lark_md） |
| image | image | ❌ 不支持（需接口） | image |
| link | 不支持 | link | 不直接支持 |
| card | template_card | actionCard | card |
| file | file | ❌ 不支持（需接口） | file |
| voice | voice | ❌ 不支持（需接口） | audio |
| news | news | feedCard | 不支持 |
| text_v1 | 不支持 | 不支持 | text（V1 纯文本） |

**说明**：
- 钉钉 Webhook 方式不支持 image、file、voice、video 类型，需要通过接口方式发送
- 企业微信支持 markdown_v2（增强版 Markdown，支持表格等）
- 飞书 V1 Webhook 仅支持纯文本，V2 支持多种消息类型

#### 4.2.2 Markdown 语法差异

| 语法 | 企业微信（标准） | 企业微信（V2） | 钉钉 | 飞书 |
|-----|-----------------|----------------|------|------|
| 加粗 | `**text**` | `**text**` | `**text**` | `**text**` |
| 斜体 | 不支持 | `*text*` | `*text*` | `*text*` |
| 链接 | `[text](url)` | `[text](url)` | `[text](url)` | `[text](url)` |
| 代码块 | \`code\` | \`\`\`code\`\`\` | 不支持 | \`\`\`code\`\`\` |
| 表格 | 不支持 | 支持 | 支持 | 不直接支持 |
| 颜色 | `<font color="xxx">` | 不支持 | 不支持 | 不支持 |
| 列表 | 不支持 | 支持 | 支持 | 支持 |
| 引用 | `> text` | `> text` | `> text` | 支持 |
| 分割线 | 不支持 | `---` | 不支持 | 不支持 |
| @成员 | `<@userid>` | 不支持 | @提及 | 支持 |
| 图片 | 不支持 | `![alt](url)` | `![alt](url)` | 支持 |

---

## 5. 消息格式化系统

### 5.1 统一消息接口

```typescript
interface WebhookMessage {
  // 消息元数据
  metadata: {
    message_id?: string,       // 消息唯一标识
    correlation_id?: string,   // 关联 ID（用于追踪）
    timestamp?: string,        // 发送时间
    priority?: "low" | "normal" | "high", // 优先级
  };
  
  // 消息内容
  content: {
    message_type: MessageType,
    title?: string,            // 可选标题
    body: MessageBody,         // 消息主体
  };
  
  // 发送选项
  options?: {
    at_users?: string[],       // @用户
    at_all?: boolean,          // @全体
    callback_url?: string,     // 回调地址
    extra_headers?: object,    // 额外请求头
  };
}

type MessageType = 
  | "text"
  | "markdown"
  | "image"
  | "link"
  | "card"
  | "file"
  | "feed";

interface MessageBody {
  text?: string;
  markdown_content?: string;
  image_url?: string;
  image_base64?: string;
  link_url?: string;
  link_title?: string;
  link_text?: string;
  card_template?: CardTemplate;
  file_url?: string;
  file_path?: string;
  feed_items?: FeedItem[];
}
```

### 5.2 平台适配器接口

```typescript
interface PlatformAdapter {
  // 平台标识
  readonly platform: string;
  
  // 验证 Webhook URL
  validateWebhookUrl(url: string): ValidationResult;
  
  // 构建请求
  buildRequest(
    webhookUrl: string,
    message: WebhookMessage
  ): HTTPRequest;
  
  // 解析响应
  parseResponse(response: HTTPResponse): SendResult;
  
  // 格式化 Markdown
  formatMarkdown(content: string): string;
  
  // 获取速率限制信息
  getRateLimitInfo(): RateLimitInfo;
}
```

### 5.3 格式化转换规则

#### 5.3.1 Markdown 转换器

```typescript
class MarkdownConverter {
  // 企业微信 Markdown 转换
  static convertToWeCom(markdown: string): string {
    let result = markdown;
    
    // 转换代码块（移除，保留内容）
    result = result.replace(/```(\w*)\n([\s\S]*?)```/g, '$2');
    
    // 转换表格（移除样式，保留结构）
    result = result.replace(/\|[^|]+\|/g, (match) => match);
    
    // 转换任务列表
    result = result.replace(/- \[ \] /g, '☐ ');
    result = result.replace(/- \[x\] /g, '☑ ');
    
    // 转换引用
    result = result.replace(/^> /gm, '> ');
    
    return result;
  }
  
  // 钉钉 Markdown 转换
  static convertToDingTalk(markdown: string): string {
    let result = markdown;
    
    // 转换代码块（移除语法，保留内容）
    result = result.replace(/```(\w*)\n([\s\S]*?)```/g, '$2');
    
    // 转换水平分割线
    result = result.replace(/^---$/gm, '___');
    
    return result;
  }
  
  // 飞书 Markdown 转换
  static convertToFeishu(markdown: string): string {
    let result = markdown;
    
    // 转换为飞书富文本格式
    // 这里需要更复杂的转换逻辑
    // 返回 JSON 格式的富文本
    
    return JSON.stringify(convertToRichText(result));
  }
}
```

### 5.4 特殊内容处理

#### 5.4.1 图片处理流程

```
用户图片输入
     │
     ▼
┌───────────────┐
│ 图片验证器    │
│ - 大小检查    │
│ - 格式检查    │
└───────────────┘
     │
     ▼
┌───────────────┐
│ 图片转换器    │
│ - 格式转换    │
│ - 压缩（可选）│
└───────────────┘
     │
     ▼
┌───────────────┐
│ 编码处理器    │
│ - Base64 编码 │
│ - MD5 计算    │
└───────────────┘
     │
     ▼
平台特定输出
```

#### 5.4.2 链接处理

不同平台对链接的处理方式不同：

| 平台 | 链接格式 | 特殊支持 |
|-----|---------|---------|
| 企业微信 | `[文本](URL)` | 支持 HTML 链接 |
| 钉钉 | `[文本](URL)` | 支持图片链接 |
| 飞书 | `{"type":"text","text":"文本","href":"URL"}` | 富文本链接 |

---

## 6. 错误处理策略

### 6.1 错误分类

```
WebHookError
├── 网络错误（NetworkError）
│   ├── ConnectionTimeout
│   ├── DNSResolutionFailed
│   └── SSLError
├── 客户端错误（ClientError）
│   ├── InvalidWebhookUrl
│   ├── InvalidMessageFormat
│   ├── UnsupportedMessageType
│   └── ContentTooLong
├── 服务器错误（ServerError）
│   ├── PlatformApiError
│   ├── RateLimitExceeded
│   └── InternalServerError
├── 认证错误（AuthError）
│   ├── InvalidCredentials
│   ├── TokenExpired
│   └── PermissionDenied
└── 内容错误（ContentError）
    ├── SensitiveContent
    ├── InvalidFormat
    └── QuotaExceeded
```

### 6.2 重试机制

#### 6.2.1 重试策略配置

```typescript
interface RetryPolicy {
  max_retries: number;           // 最大重试次数
  initial_delay: number;         // 初始延迟（毫秒）
  max_delay: number;             // 最大延迟（毫秒）
  backoff_multiplier: number;    // 退避系数
  retry_on_status: number[];     // 需要重试的状态码
  retryable_errors: string[];    // 需要重试的错误码
}
```

**默认重试策略**：

```typescript
const DEFAULT_RETRY_POLICY: RetryPolicy = {
  max_retries: 3,
  initial_delay: 1000,
  max_delay: 30000,
  backoff_multiplier: 2,
  retry_on_status: [429, 500, 502, 503, 504],
  retryable_errors: [
    'WHP004', // 网络超时
    'WHP005', // 平台 API 错误
    'WHP006', // 频率限制
  ],
};
```

#### 6.2.2 指数退避算法

```
重试间隔计算公式：
delay = min(initial_delay * (backoff_multiplier ^ attempt), max_delay) + jitter

示例（initial_delay=1000, multiplier=2, max_delay=30000）：
- 第1次重试：1-2 秒
- 第2次重试：2-4 秒
- 第3次重试：4-8 秒
- 第4次重试：8-16 秒
- 第5次重试：16-30 秒
```

### 6.3 死信队列

当消息发送失败超过最大重试次数时，消息会被移入死信队列：

```typescript
interface DeadLetterQueue {
  // 添加到死信队列
  add(message: FailedMessage): void;
  
  // 获取死信消息
  get(options?: { limit?: number; since?: Date }): FailedMessage[];
  
  // 重新处理
  retry(messageId: string): Promise<void>;
  
  // 删除
  delete(messageId: string): void;
}

interface FailedMessage {
  id: string;
  original_message: WebhookMessage;
  error: WebHookError;
  attempts: number;
  first_failure: Date;
  last_attempt: Date;
  metadata: object;
}
```

### 6.4 降级策略

当主平台不可用时，可以实施降级策略：

```
┌─────────────┐
│ 发送请求    │
└──────┬──────┘
       ▼
┌─────────────┐     失败      ┌─────────────┐
│ 主平台      │─────────────▶│ 降级平台 A  │
│ (首选)      │              │             │
└─────────────┘              └──────┬──────┘
                                    │
                          ┌─────────┴─────────┐
                          ▼                   ▼
                   成功返回              失败
                                            │
                                            ▼
                                    ┌─────────────┐
                                    │ 降级平台 B  │
                                    │ (最终备选)  │
                                    └──────┬──────┘
                                           │
                                  ┌────────┴────────┐
                                  ▼                 ▼
                           成功返回           失败（记录）
```

---

## 7. 安全性考虑

### 7.1 Webhook URL 保护

**风险**：
- Webhook URL 泄露导致消息滥用
- 恶意用户发送垃圾消息

**防护措施**：

1. **URL 验证**
   ```typescript
   function validateWebhookUrl(url: string): ValidationResult {
     // 检查 URL 格式
     if (!isValidUrl(url)) {
       return { valid: false, error: 'Invalid URL format' };
     }
     
     // 检查协议
     if (!url.startsWith('https://')) {
       return { valid: false, error: 'Only HTTPS allowed' };
     }
     
     // 检查域名白名单
     const allowedDomains = [
       'qyapi.weixin.qq.com',
       'oapi.dingtalk.com',
       'open.feishu.cn',
     ];
     
     const hostname = new URL(url).hostname;
     if (!allowedDomains.includes(hostname)) {
       return { valid: false, error: 'Domain not allowed' };
     }
     
     return { valid: true };
   }
   ```

2. **敏感信息过滤**
   ```typescript
   function sanitizeContent(content: string): string {
     // 移除潜在的敏感信息
     return content
       .replace(/[A-Za-z0-9+/]{40,}={0,2}/g, '[TOKEN]') // 移除 token
       .replace(/sk-[a-zA-Z0-9]{20,}/g, '[SECRET]');   // 移除密钥
   }
   ```

### 7.2 输入验证

```typescript
interface ValidationSchema {
  message_type: {
    type: 'enum',
    values: ['text', 'markdown', 'image', 'link', 'card', 'file'],
    required: true,
  },
  content: {
    type: 'object',
    fields: {
      text: { type: 'string', maxLength: 2048 },
      image_url: { type: 'url', allowedProtocols: ['https'] },
      image_base64: { type: 'string', pattern: /^[A-Za-z0-9+/=]+$/ },
    },
  },
  options: {
    type: 'object',
    optional: true,
    fields: {
      timeout: { type: 'number', min: 1000, max: 60000 },
      retry_count: { type: 'number', min: 0, max: 10 },
    },
  },
}
```

### 7.3 速率限制

```typescript
interface RateLimiter {
  // 滑动窗口限流
  checkRateLimit(platform: string, webhookUrl: string): boolean;
  
  // 获取剩余配额
  getRemainingQuota(platform: string, webhookUrl: string): number;
  
  // 重置计数
  resetCount(platform: string, webhookUrl: string): void;
}

// 平台限流配置
const RATE_LIMITS = {
  wecom: {
    max_requests: 20,
    window_seconds: 60,
  },
  dingtalk: {
    max_requests: 20,
    window_seconds: 60,
  },
  feishu: {
    max_requests: 100,
    window_seconds: 60,
  },
};
```

### 7.4 日志与审计

```typescript
interface AuditLog {
  timestamp: string;
  request_id: string;
  platform: string;
  message_type: string;
  webhook_url_hash: string;  // 脱敏
  status: 'success' | 'failed' | 'retry';
  error_code?: string;
  duration_ms: number;
  retry_count: number;
  metadata: object;
}
```

---

## 8. 配置选项

### 8.1 环境变量配置

```bash
# 企业微信
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
WECOM_TIMEOUT=5000
WECOM_RETRY_COUNT=3

# 钉钉
DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=xxx
DINGTALK_SECRET=xxx
DINGTALK_TIMEOUT=5000
DINGTALK_RETRY_COUNT=3

# 飞书
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
FEISHU_APP_ID=xxx
FEISHU_APP_SECRET=xxx
FEISHU_TIMEOUT=5000
FEISHU_RETRY_COUNT=3

# 通用配置
DEFAULT_TIMEOUT=5000
DEFAULT_RETRY_COUNT=3
LOG_LEVEL=info
ENABLE_AUDIT_LOG=true
```

### 8.2 配置文件

支持 JSON、YAML、ENV 格式的配置文件：

```yaml
# webhook-push.config.yaml
platforms:
  wecom:
    enabled: true
    webhook_url: ${WECOM_WEBHOOK_URL}
    timeout: 5000
    retry:
      max_retries: 3
      initial_delay: 1000
      backoff_multiplier: 2

  dingtalk:
    enabled: true
    webhook_url: ${DINGTALK_WEBHOOK_URL}
    secret: ${DINGTALK_SECRET}
    timeout: 5000
    retry:
      max_retries: 3

  feishu:
    enabled: true
    webhook_url: ${FEISHU_WEBHOOK_URL}
    timeout: 5000
    retry:
      max_retries: 3

defaults:
  message_type: markdown
  timeout: 5000
  retry_count: 3

logging:
  level: info
  audit_enabled: true
```

---

## 9. 使用示例

### 9.1 企业微信示例

**发送文本消息**：
```typescript
await send_webhook_message({
  platform: "wecom",
  webhook_url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx",
  message_type: "text",
  content: {
    text: "这是一个测试消息",
    at_users: ["user123"]
  }
});
```

**发送标准 Markdown 消息**：
```typescript
await send_webhook_message({
  platform: "wecom",
  webhook_url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx",
  message_type: "markdown",
  content: {
    title: "告警通知",
    text: `**服务器告警**
> 告警级别：高
> 告警内容：CPU 使用率超过 90%

- 服务器：web-01
- CPU：95%
- 内存：82%

<font color="warning">请及时处理！</font>`
  }
});
```

**发送 Markdown V2 消息**（支持表格等高级语法）：
```typescript
await send_webhook_message({
  platform: "wecom",
  webhook_url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx",
  message_type: "markdown_v2",
  content: {
    title: "数据报告",
    text: `# 今日数据报告

## 核心指标
*新增用户：128*
**活跃用户：3,421**

## 转化漏斗
| 阶段 | 人数 | 转化率 |
| :--- | ---: | ---: |
| 访问 | 10,000 | 100% |
| 注册 | 3,500 | 35% |
| 付费 | 1,200 | 34% |

---
数据更新时间：18:00`
  }
});
```

**发送图片消息**：
```typescript
import * as fs from 'fs';
import * as crypto from 'crypto';

await send_webhook_message({
  platform: "wecom",
  webhook_url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx",
  message_type: "image",
  content: {
    image_base64: fs.readFileSync('/path/to/image.jpg').toString('base64'),
    image_md5: crypto.createHash('md5').update(fs.readFileSync('/path/to/image.jpg')).digest('hex')
  }
});
```

**发送图文消息**：
```typescript
await send_webhook_message({
  platform: "wecom",
  webhook_url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx",
  message_type: "news",
  content: {
    articles: [
      {
        title: "产品更新公告",
        description: "本次更新带来了多项新功能",
        url: "https://example.com/updates",
        picurl: "https://example.com/cover.jpg"
      },
      {
        title: "使用指南",
        description: "新功能使用指南",
        url: "https://example.com/guide",
        picurl: "https://example.com/guide.jpg"
      }
    ]
  }
});
```

**发送模板卡片 - 文本通知**：
```typescript
await send_webhook_message({
  platform: "wecom",
  webhook_url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx",
  message_type: "template_card",
  content: {
    card_type: "text_notice",
    source: {
      icon_url: "https://example.com/icon.png",
      desc: "监控系统"
    },
    main_title: {
      title: "服务器告警",
      desc: "CPU 使用率异常"
    },
    emphasis_content: {
      title: "95%",
      desc: "当前 CPU 使用率"
    },
    horizontal_content_list: [
      { keyname: "服务器", value: "web-01" },
      { keyname: "告警级别", value: "严重", type: 1, url: "https://example.com/level" }
    ],
    jump_list: [
      { type: 1, url: "https://example.com/details", title: "查看详情" }
    ]
  }
});
```

### 9.2 钉钉示例

**发送文本消息**：
```typescript
await send_webhook_message({
  platform: "dingtalk",
  webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=xxx",
  message_type: "text",
  content: {
    text: "这是一条测试消息",
    at_users: ["13800000000"],  // @指定手机号用户
    at_all: false
  }
});
```

**发送 @全体成员消息**：
```typescript
await send_webhook_message({
  platform: "dingtalk",
  webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=xxx",
  message_type: "text",
  content: {
    text: "请大家注意，明天上午 10 点开会",
    at_all: true
  }
});
```

**发送 Markdown 消息**：
```typescript
await send_webhook_message({
  platform: "dingtalk",
  webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=xxx",
  message_type: "markdown",
  content: {
    title: "每日数据报告",
    text: `# 今日数据概览

## 核心指标
- **新增用户**: 128
- *活跃用户*: 3,421
- 转化率: 5.2%

## 详细数据
| 指标 | 数值 | 环比 |
|-----|------|-----|
| UV | 10,000 | +5% |
| PV | 50,000 | +3% |
| 订单 | 500 | +10% |

> 数据更新时间: 2024-01-01 18:00`
  }
});
```

**发送链接消息**：
```typescript
await send_webhook_message({
  platform: "dingtalk",
  webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=xxx",
  message_type: "link",
  content: {
    link_title: "项目更新通知",
    link_text: "点击查看项目最新更新详情，包括新功能介绍和修复的问题",
    link_url: "https://example.com/project-update",
    link_image_url: "https://example.com/cover.jpg"
  }
});
```

**发送 ActionCard 单按钮消息**：
```typescript
await send_webhook_message({
  platform: "dingtalk",
  webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=xxx",
  message_type: "actionCard",
  content: {
    card_type: "single",
    title: "告警通知",
    text: `**服务器 CPU 使用率过高**

> 当前使用率：95%
> 服务器：web-01

请及时处理此告警！`,
    hide_avatar: "0",
    btn_orientation: "0",
    single_title: "查看详情",
    single_url: "https://example.com/alerts/detail"
  }
});
```

**发送 ActionCard 多按钮消息**：
```typescript
await send_webhook_message({
  platform: "dingtalk",
  webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=xxx",
  message_type: "actionCard",
  content: {
    card_type: "multi",
    title: "请选择操作",
    text: `您有一个待审批的任务，请选择操作：`,
    hide_avatar: "0",
    btn_orientation: "1",
    btns: [
      {
        title: "通过",
        action_url: "https://example.com/approve?id=123"
      },
      {
        title: "拒绝",
        action_url: "https://example.com/reject?id=123"
      },
      {
        title: "查看详情",
        action_url: "https://example.com/detail?id=123"
      }
    ]
  }
});
```

**发送 FeedCard 图文消息**：
```typescript
await send_webhook_message({
  platform: "dingtalk",
  webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=xxx",
  message_type: "feedCard",
  content: {
    links: [
      {
        title: "今日技术头条",
        message_url: "https://example.com/news/1",
        pic_url: "https://example.com/images/tech-news.png"
      },
      {
        title: "产品更新日志",
        message_url: "https://example.com/news/2",
        pic_url: "https://example.com/images/product-update.png"
      },
      {
        title: "行业动态",
        message_url: "https://example.com/news/3",
        pic_url: "https://example.com/images/industry-news.png"
      }
    ]
  }
});
```

**使用加签发送消息**：
```typescript
import * as crypto from 'crypto';

async function sendWithSign() {
  const timestamp = Date.now().toString();
  const secret = "your-signing-secret";
  const stringToSign = `${timestamp}\n${secret}`;
  const signature = crypto
    .createHmac('sha256', secret)
    .update(stringToSign)
    .digest('base64');

  await send_webhook_message({
    platform: "dingtalk",
    webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=xxx",
    message_type: "text",
    content: {
      text: "使用加签的安全消息"
    },
    headers: {
      "Timestamp": timestamp,
      "Sign": signature
    }
  });
}
```

**使用 msgUuid 实现消息去重**：
```typescript
await send_webhook_message({
  platform: "dingtalk",
  webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=xxx",
  message_type: "text",
  content: {
    text: "这是一条去重消息",
    msg_uuid: "unique-message-id-12345"  // 用于幂等控制
  }
});
```

### 9.3 飞书示例

**发送简单文本消息**：
```typescript
await send_webhook_message({
  platform: "feishu",
  webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
  message_type: "text",
  content: {
    text: "这是一条来自机器人的消息"
  }
});
```

**发送富文本消息（post）**：
```typescript
await send_webhook_message({
  platform: "feishu",
  webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
  message_type: "post",
  content: {
    post: {
      zh_cn: {
        title: "项目更新通知",
        content: [
          [
            { type: "text", text: "各位同事，" },
            { type: "at", user_id: "ou_xxx", user_name: "张三" },
            { type: "text", text: "项目有新更新：" }
          ],
          [
            { type: "lark_md", text: "**功能更新**" },
            { type: "text", text: "- 支持批量操作" },
            { type: "text", text: "- 性能优化 30%" }
          ],
          [
            { type: "url", url: "https://example.com", text: "点击查看详情" }
          ]
        ]
      }
    }
  }
});
```

**发送交互式卡片消息**：
```typescript
await send_webhook_message({
  platform: "feishu",
  webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
  message_type: "card",
  content: {
    config: {
      wide_screen_mode: true,
      enable_forward: true
    },
    header: {
      template: "blue",
      title: {
        content: "告警通知",
        tag: "plain_text"
      }
    },
    elements: [
      {
        tag: "div",
        text: {
          content: "**服务器 CPU 使用率过高**\n当前使用率：95%",
          tag: "lark_md"
        }
      },
      {
        tag: "div",
        text: {
          content: "服务器：web-01\n告警时间：2024-01-01 12:00:00",
          tag: "plain_text"
        }
      },
      { tag: "hr" },
      {
        tag: "action",
        actions: [
          {
            tag: "button",
            text: {
              content: "查看详情",
              tag: "plain_text"
            },
            type: "primary",
            url: "https://example.com/alerts"
          },
          {
            tag: "button",
            text: {
              content: "稍后处理",
              tag: "plain_text"
            },
            type: "default"
          }
        ]
      },
      {
        tag: "note",
        elements: [
          { tag: "plain_text", content: "💡 请尽快处理此告警" }
        ]
      }
    ]
  }
});
```

**发送图片消息**（需要先上传获取 image_key）：
```typescript
// 假设已通过上传接口获取 image_key
await send_webhook_message({
  platform: "feishu",
  webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
  message_type: "image",
  content: {
    image_key: "img_v2_cb03ec35-a638-4b93-9e6f-5e2d0e549deg"
  }
});
```

**V1 Webhook 纯文本消息**（仅支持纯文本，已废弃）：
```typescript
// V1 格式，仅支持纯文本
await send_webhook_message({
  platform: "feishu",
  webhook_url: "https://open.feishu.cn/open-apis/bot/hook/xxx",
  message_type: "text_v1",
  content: {
    title: "通知",
    text: "这是一条简单的文本消息"
  }
});
```

### 9.4 批量发送示例

```typescript
const results = await send_batch_webhook_messages({
  messages: [
    {
      platform: "wecom",
      webhook_url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx1",
      message_type: "text",
      content: { text: "企业微信通知" }
    },
    {
      platform: "dingtalk",
      webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=xxx2",
      message_type: "markdown",
      content: { title: "钉钉通知", text: "## 钉钉消息" }
    },
    {
      platform: "feishu",
      webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/xxx3",
      message_type: "text",
      content: { text: "飞书通知" }
    }
  ],
  options: {
    concurrency: 3,
    continue_on_error: true
  }
});

console.log(`成功: ${results.success_count}, 失败: ${results.failed_count}`);
```

### 9.5 最佳实践

1. **消息模板化**
   ```typescript
   // 定义消息模板
   const alertTemplate = (server: string, cpu: number) => ({
     platform: "wecom",
     message_type: "markdown",
     content: {
       title: "服务器告警",
       text: `**${server}** CPU 使用率达到 **${cpu}%**
       
> 请及时处理！`
     }
   });
   ```

2. **错误处理**
   ```typescript
   try {
     const result = await send_webhook_message({
       platform: "wecom",
       webhook_url: url,
       message_type: "text",
       content: { text: "消息" }
     });
     
     if (!result.success) {
       if (result.retry_suggested) {
         // 重新入队等待重试
         await retryQueue.add(result);
       } else {
         // 记录到监控系统
         monitor.reportError(result.error);
       }
     }
   } catch (error) {
     logger.error("Unexpected error:", error);
   }
   ```

3. **异步发送**
   ```typescript
   // 使用异步模式，避免阻塞
   const result = await send_webhook_message({
     platform: "wecom",
     webhook_url: url,
     message_type: "text",
     content: { text: "消息" },
     options: {
       async_mode: true
     }
   });
   ```

---

## 10. 实施路线图

### 10.1 第一阶段：核心功能

**目标**：完成基本的消息发送功能

| 功能 | 优先级 | 预估工作量 |
|-----|--------|-----------|
| 基础架构搭建 | P0 | 2 天 |
| 企业微信适配器 | P0 | 3 天 |
| 钉钉适配器 | P0 | 3 天 |
| 飞书适配器 | P0 | 3 天 |
| 统一 API 接口 | P0 | 2 天 |
| 基础错误处理 | P0 | 2 天 |
| 文档编写 | P1 | 2 天 |

**交付物**：
- 完整的核心代码库
- 基础使用文档
- API 参考文档

### 10.2 第二阶段：高级功能

**目标**：增强可靠性和用户体验

| 功能 | 优先级 | 预估工作量 |
|-----|--------|-----------|
| 高级重试机制 | P1 | 3 天 |
| 死信队列 | P1 | 2 天 |
| 消息格式化器 | P1 | 3 天 |
| 速率限制器 | P1 | 2 天 |
| 配置管理 | P1 | 2 天 |
| 审计日志 | P2 | 2 天 |
| 单元测试 | P0 | 3 天 |

**交付物**：
- 增强版代码库
- 配置指南
- 测试报告

### 10.3 第三阶段：优化与监控

**目标**：生产环境就绪

| 功能 | 优先级 | 预估工作量 |
|-----|--------|-----------|
| 性能优化 | P1 | 2 天 |
| 监控指标 | P1 | 2 天 |
| 健康检查 | P1 | 1 天 |
| 降级策略 | P2 | 3 天 |
| 压测报告 | P2 | 2 天 |
| 部署文档 | P1 | 1 天 |

**交付物**：
- 优化后的代码库
- 监控配置
- 部署指南

---

## 11. 附录

### 11.1 Webhook URL 快速参考

| 平台 | URL 版本 | URL 格式 | 支持消息类型 |
|-----|---------|---------|-------------|
| 企业微信 | V1 | `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={KEY}` | text, markdown, markdown_v2, image, news, file, voice, template_card |
| 钉钉 | V1 | `https://oapi.dingtalk.com/robot/send?access_token={TOKEN}` | text, markdown, link, actionCard, feedCard |
| 飞书 | V2（推荐） | `https://open.feishu.cn/open-apis/bot/v2/hook/{ID}` | text, post, image, file, card, audio, share_chat, share_user |
| 飞书 | V1（废弃） | `https://open.feishu.cn/open-apis/bot/hook/{ID}` | text（仅纯文本） |

### 11.2 错误码速查表

| 错误码 | 说明 | 平台 | 处理建议 |
|-------|------|------|---------|
| WHP001 | 无效 Webhook URL | 通用 | 检查 URL 格式 |
| WHP002 | 不支持消息类型 | 通用 | 更换消息类型 |
| WHP003 | 内容格式错误 | 通用 | 修复格式 |
| WHP004 | 网络超时 | 通用 | 重试 |
| WHP005 | 平台 API 错误 | 通用 | 检查错误详情 |
| WHP006 | 频率限制 | 通用 | 降级发送 |
| WHP007 | 敏感词 | 通用 | 修改内容 |
| WHP008 | 凭证无效 | 通用 | 检查配置 |
| WHP009 | 内容过长 | 通用 | 截断或分片 |
| WHP010 | 文件过大 | 通用 | 压缩或分片 |
| 0 | 成功 | 企业微信 | - |
| -1 | 系统繁忙 | 企业微信 | 稍后重试 |
| 40001 | 获取 access_token 失败 | 企业微信 | 检查凭证配置 |
| 40014 | access_token 无效 | 企业微信 | 刷新 token |
| 41004 | 缺少 access_token | 企业微信 | 检查请求参数 |
| 60004 | Key 无效 | 企业微信 | 检查 Key 配置 |
| 60020 | IP 不在白名单 | 企业微信 | 配置 IP 白名单 |
| 60009 | 内容包含敏感词 | 企业微信 | 修改内容 |
| 60008 | 请求过于频繁 | 企业微信 | 限流后重试 |
| 0 | 成功 | 钉钉 | - |
| 40001 | 获取 access_token 失败 | 钉钉 | 检查 access_token |
| 40014 | access_token 无效 | 钉钉 | 刷新 access_token |
| 41004 | 缺少 access_token | 钉钉 | 检查请求参数 |
| 30001 | 机器人消息频率超限 | 钉钉 | 降级发送，等待 10 分钟后重试 |
| 30002 | 机器人被禁言 | 钉钉 | 检查机器人状态 |
| 30003 | 超过群成员限制 | 钉钉 | 无法发送 |
| 30004 | 消息内容包含敏感词 | 钉钉 | 修改内容 |
| 30100 | 参数不完整 | 钉钉 | 检查请求参数 |
| 0 | 成功 | 飞书 | - |
| 216100 | 消息内容过长 | 飞书 | 截断或分片 |
| 216401 | Webhook Key 不存在 | 飞书 | 检查 Webhook ID |
| 216403 | 无发送权限 | 飞书 | 检查机器人配置 |
| 216429 | 请求过于频繁 | 飞书 | 降级发送 |
| 216500 | 无效的 JSON | 飞书 | 检查请求格式 |
| 216613 | 消息类型不支持 | 飞书 | 使用支持的消息类型 |
| 216629 | 消息频率超限 | 飞书 | 降级发送 |

### 11.3 平台文档链接

| 平台 | 文档类型 | 官方文档 |
|-----|---------|---------|
| 企业微信 | 消息推送 | https://developer.work.weixin.qq.com/document/path/99110 |
| 钉钉 | 自定义机器人 Webhook | https://open.dingtalk.com/document/dingstart/obtain-the-webhook-address-of-a-custom-robot |
| 钉钉 | 发送消息类型 | https://open.dingtalk.com/document/dingstart/custom-bot-send-message-type |
| 飞书 | 自定义机器人 | https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot |
| 飞书 | 卡片消息 | https://open.feishu.cn/document/uAjLw4CM/ukzMukzMukzM/feishu-cards/send-feishu-card |
| 飞书 | 富文本 | https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/im-v1/message/create |

### 11.4 术语表

| 术语 | 说明 | 适用平台 |
|-----|------|---------|
| Webhook | 一种通过 HTTP POST 实现的消息推送机制 | 通用 |
| Webhook Key | 企业微信群机器人的唯一标识 | 企业微信 |
| Access Token | 钉钉机器人发送消息的访问令牌 | 钉钉 |
| Webhook ID | 飞书自定义机器人的唯一标识 | 飞书 |
| Rate Limiting | 平台对消息发送频率的限制机制 | 通用 |
| Dead Letter Queue | 死信队列，存放无法发送的消息 | 通用 |
| Exponential Backoff | 指数退避，重试间隔逐渐增加的策略 | 通用 |
| Image Key | 飞书图片上传后返回的唯一标识 | 飞书 |
| Media ID | 企业微信/钉钉素材上传后返回的唯一标识 | 企业微信、钉钉 |
| lark_md | 飞书支持的 Markdown 标签 | 飞书 |
| Wide Screen Mode | 飞书卡片的宽屏显示模式 | 飞书 |
| Template Card | 企业微信的模板卡片消息 | 企业微信 |
| Action Card | 钉钉的互动卡片消息 | 钉钉 |
| Markdown_v2 | 企业微信增强版 Markdown 语法 | 企业微信 |

---

*文档版本：1.2*  
*最后更新：2025 年 1 月*  
*作者：Webhook Push Skill 设计团队*

**更新日志**：
- v1.2（2025-01）：根据钉钉官方文档更新钉钉自定义机器人部分，添加完整的消息类型（text/markdown/link/actionCard/feedCard）、加签安全机制、msgUuid 消息去重、错误码详情、使用示例
- v1.1（2025-01）：根据飞书官方文档更新飞书自定义机器人部分，添加 V1/V2 Webhook 区分、富文本消息详解、卡片组件说明、完整错误码列表
- v1.0（2024-01）：初始版本，支持企业微信、钉钉、飞书三大平台
