# Webhook Push Skill - 通用消息设计

## 1. 概述

### 1.1 设计目标

本文档定义了 `webhook-push` 技能的通用消息设计方案，旨在提供一个与平台无关的消息抽象层，使得上层业务逻辑无需关心底层平台的差异性。

**核心设计原则**：

1. **平台无关性**：业务代码使用统一的消息格式，与具体平台解耦
2. **渐进式降级**：当平台不支持某功能时，自动降级到基础功能
3. **语义一致性**：相同语义的消息在不同平台保持一致的体验
4. **可扩展性**：易于添加新的平台支持
5. **最小化依赖**：仅依赖必要的平台能力

### 1.2 支持平台矩阵

| 特性 | 企业微信 | 钉钉 | 飞书 |
|-----|---------|------|------|
| 文本消息 | ✅ | ✅ | ✅ |
| Markdown | ✅（2种） | ✅ | ✅（lark_md） |
| 图片 | ✅ | ❌（Webhook） | ✅ |
| 文件 | ✅ | ❌（Webhook） | ✅ |
| 卡片 | ✅（模板） | ✅（ActionCard） | ✅（交互） |
| @提及 | ✅ | ✅ | ✅ |
| 按钮交互 | ✅ | ✅ | ✅ |
| 频率限制 | 20/分钟 | 20/分钟 | 无明确限制 |

### 1.3 消息能力分级

```
Level 0: 基础文本
├── 纯文本内容
└── @提及

Level 1: 富文本
├── Markdown 格式
├── 图片
├── 链接
└── 列表/表格

Level 2: 交互式
├── 按钮
├── 表单
└── 回调

Level 3: 多媒体
├── 文件
├── 语音
└── 视频
```

---

## 2. 统一消息模型

### 2.1 消息结构定义

```typescript
/**
 * 统一消息接口
 * 平台无关的消息抽象
 */
interface UnifiedMessage {
  // 消息元数据
  metadata: MessageMetadata;
  
  // 消息内容
  content: MessageContent;
  
  // 发送选项
  options?: SendOptions;
}

/**
 * 消息元数据
 */
interface MessageMetadata {
  // 消息唯一标识（用于追踪和去重）
  message_id?: string;
  
  // 关联 ID（用于关联相关消息）
  correlation_id?: string;
  
  // 消息优先级
  priority?: MessagePriority;
  
  // 消息来源
  source?: string;
  
  // 创建时间
  created_at?: string;
}

/**
 * 消息优先级
 */
enum MessagePriority {
  LOW = "low",
  NORMAL = "normal",
  HIGH = "high",
  URGENT = "urgent"
}

/**
 * 消息内容
 */
interface MessageContent {
  // 消息类型
  type: MessageType;
  
  // 标题（部分平台支持）
  title?: string;
  
  // 主要内容
  body: MessageBody;
  
  // 媒体附件
  media?: MediaAttachment[];
  
  // 交互组件
  actions?: ActionComponent[];
  
  // @提及用户
  mentions?: Mention[];
}

/**
 * 消息类型
 */
enum MessageType {
  TEXT = "text",
  MARKDOWN = "markdown",
  IMAGE = "image",
  LINK = "link",
  CARD = "card",
  FILE = "file",
  FEED = "feed"
}

/**
 * 消息体
 */
type MessageBody = 
  | TextBody
  | MarkdownBody
  | ImageBody
  | LinkBody
  | CardBody
  | FileBody
  | FeedBody;
```

### 2.2 具体消息体定义

#### 2.2.1 文本消息

```typescript
/**
 * 文本消息体
 */
interface TextBody {
  // 文本内容
  text: string;
}

/**
 * 示例
 */
const textMessage: UnifiedMessage = {
  metadata: {
    message_id: "msg_001",
    priority: "normal"
  },
  content: {
    type: "text",
    title: "通知",
    body: {
      text: "这是一条文本消息"
    },
    mentions: [
      { type: "mobile", value: "13800000000" }
    ]
  }
};
```

#### 2.2.2 Markdown 消息

```typescript
/**
 * Markdown 消息体
 */
interface MarkdownBody {
  // Markdown 内容
  content: string;
  
  // 是否使用增强版 Markdown（企业微信 V2）
  enhanced?: boolean;
}

/**
 * Markdown 变体支持
 */
enum MarkdownVariant {
  STANDARD = "standard",    // 标准 Markdown
  WECOM_V2 = "wecom_v2",    // 企业微信增强版
  FEISHU = "feishu"         // 飞书 lark_md
}

/**
 * 示例
 */
const markdownMessage: UnifiedMessage = {
  metadata: {
    message_id: "msg_002"
  },
  content: {
    type: "markdown",
    title: "数据报告",
    body: {
      content: `# 今日数据

## 核心指标
- 新增用户：**128**
- 活跃用户：3,421

> 数据更新时间：18:00`
    }
  }
};
```

#### 2.2.3 图片消息

```typescript
/**
 * 图片消息体
 */
interface ImageBody {
  // 图片 URL
  url?: string;
  
  // Base64 编码（企业微信需要）
  base64?: string;
  
  // MD5 校验值（企业微信需要）
  md5?: string;
  
  // 图片描述
  alt?: string;
}

/**
 * 示例
 */
const imageMessage: UnifiedMessage = {
  metadata: {
    message_id: "msg_003"
  },
  content: {
    type: "image",
    body: {
      url: "https://example.com/screenshot.png",
      alt: "系统监控截图"
    }
  }
};
```

#### 2.2.4 链接消息

```typescript
/**
 * 链接消息体
 */
interface LinkBody {
  // 链接标题
  title: string;
  
  // 链接描述
  text?: string;
  
  // 跳转 URL
  url: string;
  
  // 图片 URL
  image_url?: string;
}

/**
 * 示例
 */
const linkMessage: UnifiedMessage = {
  metadata: {
    message_id: "msg_004"
  },
  content: {
    type: "link",
    body: {
      title: "项目更新公告",
      text: "点击查看最新功能更新",
      url: "https://example.com/updates",
      image_url: "https://example.com/cover.png"
    }
  }
};
```

#### 2.2.5 卡片消息

```typescript
/**
 * 卡片消息体
 */
interface CardBody {
  // 卡片类型
  card_type: CardType;
  
  // 卡片配置
  config?: CardConfig;
  
  // 卡片元素
  elements: CardElement[];
  
  // 卡片动作
  actions?: CardAction[];
}

/**
 * 卡片类型
 */
enum CardType {
  // 企业微信
  TEXT_NOTICE = "text_notice",      // 文本通知
  NEWS_SHOW = "news_show",          // 图文展示
  
  // 钉钉
  ACTION_CARD_SINGLE = "single",    // 单按钮
  ACTION_CARD_MULTI = "multi",      // 多按钮
  
  // 飞书
  INTERACTIVE = "interactive",      // 交互卡片
  TEMPLATE = "template"             // 模板卡片
}

/**
 * 卡片配置
 */
interface CardConfig {
  // 宽屏模式（飞书）
  wide_screen_mode?: boolean;
  
  // 允许转发（飞书）
  enable_forward?: boolean;
  
  // 隐藏发送者头像（钉钉）
  hide_avatar?: string;
  
  // 按钮排列方向（钉钉）："0" 垂直，"1" 水平
  btn_orientation?: string;
}

/**
 * 卡片元素
 */
type CardElement = 
  | TextElement
  | ImageElement
  | DivElement
  | HrElement
  | NoteElement;

/**
 * 卡片动作
 */
interface CardAction {
  // 动作类型
  type: ActionType;
  
  // 显示文本
  text: string;
  
  // 跳转 URL
  url?: string;
  
  // 动作值（用于回调识别）
  value?: Record<string, any>;
  
  // 样式
  style?: "default" | "primary" | "danger";
}

/**
 * 动作类型
 */
enum ActionType {
  BUTTON = "button",
  LINK = "link",
  CALLBACK = "callback"
}

/**
 * 示例：钉钉 ActionCard
 */
const dingtalkCard: UnifiedMessage = {
  metadata: {
    message_id: "msg_005"
  },
  content: {
    type: "card",
    body: {
      card_type: "multi",
      config: {
        btn_orientation: "1"
      },
      elements: [
        {
          type: "text",
          text: "请选择操作："
        }
      ],
      actions: [
        {
          type: "button",
          text: "通过",
          url: "https://example.com/approve",
          value: { action: "approve" },
          style: "primary"
        },
        {
          type: "button",
          text: "拒绝",
          url: "https://example.com/reject",
          value: { action: "reject" }
        }
      ]
    }
  }
};

/**
 * 示例：飞书交互卡片
 */
const feishuCard: UnifiedMessage = {
  metadata: {
    message_id: "msg_006"
  },
  content: {
    type: "card",
    body: {
      card_type: "interactive",
      config: {
        wide_screen_mode: true
      },
      elements: [
        {
          tag: "div",
          text: {
            content: "**告警通知**\n服务器 CPU 使用率过高",
            tag: "lark_md"
          }
        },
        {
          tag: "action",
          actions: [
            {
              tag: "button",
              text: { content: "查看详情", tag: "plain_text" },
              type: "primary",
              url: "https://example.com/detail"
            }
          ]
        }
      ]
    }
  }
};
```

#### 2.2.6 文件消息

```typescript
/**
 * 文件消息体
 */
interface FileBody {
  // 文件 URL
  url?: string;
  
  // 文件 ID（需要先上传）
  media_id?: string;
  
  // 文件名
  file_name?: string;
  
  // 文件类型
  file_type?: string;
}

/**
 * 示例
 */
const fileMessage: UnifiedMessage = {
  metadata: {
    message_id: "msg_007"
  },
  content: {
    type: "file",
    body: {
      media_id: "media_123456",
      file_name: "report.pdf",
      file_type: "pdf"
    }
  }
};
```

#### 2.2.7 Feed 消息

```typescript
/**
 * Feed 消息体（图文链接组）
 */
interface FeedBody {
  // 链接列表
  links: FeedLink[];
}

/**
 * Feed 链接项
 */
interface FeedLink {
  // 标题
  title: string;
  
  // 跳转 URL
  url: string;
  
  // 图片 URL
  image_url: string;
}

/**
 * 示例
 */
const feedMessage: UnifiedMessage = {
  metadata: {
    message_id: "msg_008"
  },
  content: {
    type: "feed",
    body: {
      links: [
        {
          title: "今日头条",
          url: "https://example.com/news/1",
          image_url: "https://example.com/img1.png"
        },
        {
          title: "产品更新",
          url: "https://example.com/news/2",
          image_url: "https://example.com/img2.png"
        }
      ]
    }
  }
};
```

### 2.3 @提及支持

```typescript
/**
 * @提及配置
 */
interface Mention {
  // 提及类型
  type: MentionType;
  
  // 提及值
  value: string;
  
  // 显示名称（可选）
  display_name?: string;
}

/**
 * 提及类型
 */
enum MentionType {
  USER_ID = "user_id",      // 用户 ID
  MOBILE = "mobile",        // 手机号
  DEPARTMENT = "department", // 部门
  ALL = "all"               // @全体
}

/**
 * @全体成员
 */
const atAll: Mention = {
  type: "all"
};

/**
 * @指定用户
 */
const atUser: Mention = {
  type: "mobile",
  value: "13800000000",
  display_name: "张三"
};
```

---

## 3. 平台适配器接口

### 3.1 适配器接口定义

```typescript
/**
 * 平台适配器接口
 */
interface PlatformAdapter {
  // 平台标识
  readonly platform: string;
  
  // 平台优先级（数字越小优先级越高）
  readonly priority: number;
  
  // 检查适配器是否可用
  isAvailable(): boolean;
  
  // 验证消息是否支持
  supports(message: UnifiedMessage): SupportLevel;
  
  // 转换统一消息到平台格式
  transform(message: UnifiedMessage): PlatformPayload;
  
  // 解析平台响应
  parseResponse(response: PlatformResponse): SendResult;
  
  // 获取速率限制信息
  getRateLimitInfo(): RateLimitInfo;
}

/**
 * 支持级别
 */
enum SupportLevel {
  FULL = "full",      // 完全支持
  PARTIAL = "partial", // 部分支持（自动降级）
  NONE = "none"       // 不支持
}

/**
 * 平台负载（转换后的请求体）
 */
interface PlatformPayload {
  // 请求体
  body: Record<string, any>;
  
  // 请求头（可选）
  headers?: Record<string, string>;
  
  // 查询参数（可选）
  query?: Record<string, string>;
  
  // 转换警告
  warnings?: string[];
}

/**
 * 发送结果
 */
interface SendResult {
  // 是否成功
  success: boolean;
  
  // 平台返回的消息 ID
  message_id?: string;
  
  // 错误信息
  error?: PlatformError;
  
  // 是否建议重试
  retry_suggested?: boolean;
}

/**
 * 平台错误
 */
interface PlatformError {
  // 错误码
  code: number | string;
  
  // 错误消息
  message: string;
  
  // 错误详情
  details?: Record<string, any>;
}

/**
 * 速率限制信息
 */
interface RateLimitInfo {
  // 最大请求数
  max_requests: number;
  
  // 时间窗口（秒）
  window_seconds: number;
  
  // 剩余请求数
  remaining: number;
  
  // 重置时间
  reset_at?: string;
}
```

### 3.2 适配器注册中心

```typescript
/**
 * 适配器注册中心
 */
class AdapterRegistry {
  private adapters: Map<string, PlatformAdapter> = new Map();
  
  // 注册适配器
  register(adapter: PlatformAdapter): void {
    this.adapters.set(adapter.platform, adapter);
  }
  
  // 获取适配器
  get(platform: string): PlatformAdapter | undefined {
    return this.adapters.get(platform);
  }
  
  // 获取所有适配器
  getAll(): PlatformAdapter[] {
    return Array.from(this.adapters.values());
  }
  
  // 根据优先级获取适配器
  getByPriority(): PlatformAdapter[] {
    return this.getAll().sort((a, b) => a.priority - b.priority);
  }
  
  // 检查消息支持
  canSend(message: UnifiedMessage): PlatformAdapter[] {
    return this.getAll().filter(
      adapter => adapter.supports(message) !== SupportLevel.NONE
    );
  }
}

// 全局注册中心
export const adapterRegistry = new AdapterRegistry();
```

---

## 4. 消息转换器

### 4.1 转换器接口

```typescript
/**
 * 消息转换器
 */
interface MessageConverter {
  // 转换统一消息到平台格式
  convert(message: UnifiedMessage): PlatformPayload;
  
  // 转换平台响应到统一格式
  convertResult(result: PlatformResponse): SendResult;
  
  // 获取支持级别
  getSupportLevel(message: UnifiedMessage): SupportLevel;
  
  // 获取降级后的消息
  downgrade(message: UnifiedMessage): UnifiedMessage;
}

/**
 * 平台响应
 */
interface PlatformResponse {
  // 状态码
  status_code: number;
  
  // 响应体
  body: Record<string, any>;
  
  // 响应头
  headers?: Record<string, string>;
}
```

### 4.2 Markdown 转换器

```typescript
/**
 * Markdown 转换器
 */
class MarkdownConverter {
  // 平台特定语法映射
  private static readonly SYNTAX_MAP: Record<string, Record<string, string>> = {
    wecom_standard: {
      bold: "**text**",
      italic: null, // 不支持
      color: '<font color="xxx">text</font>',
      at: "<@userid>"
    },
    wecom_v2: {
      bold: "**text**",
      italic: "*text*",
      color: null, // 不支持
      at: null     // 不支持
    },
    dingtalk: {
      bold: "**text**",
      italic: "*text*",
      color: null,
      at: "@{userId}"
    },
    feishu: {
      bold: "**text**",
      italic: "*text*",
      color: null,
      at: "<at id='userId'></at>"
    }
  };
  
  /**
   * 转换为指定平台的 Markdown
   */
  static convert(content: string, platform: string): {
    converted: string;
    warnings: string[];
  } {
    const warnings: string[] = [];
    const syntax = this.SYNTAX_MAP[platform] || {};
    
    let result = content;
    
    // 转换加粗
    if (syntax.bold) {
      result = result.replace(/\*\*(.+?)\*\*/g, syntax.bold.replace("text", "$1"));
    } else if (platform !== "wecom_standard") {
      warnings.push("加粗语法可能不被支持");
    }
    
    // 转换斜体
    if (syntax.italic) {
      result = result.replace(/\*(.+?)\*/g, syntax.italic.replace("text", "$1"));
    } else if (!syntax.italic && platform !== "wecom_standard") {
      warnings.push("斜体语法可能不被支持");
    }
    
    return { converted: result, warnings };
  }
  
  /**
   * 降级 Markdown 为纯文本
   */
  static downgrade(content: string): string {
    // 移除 Markdown 格式，保留基本内容
    return content
      .replace(/\*\*(.+?)\*\*/g, "$1")           // 移除加粗
      .replace(/\*(.+?)\*/g, "$1")               // 移除斜体
      .replace(/`(.+?)`/g, "$1")                 // 移除代码标记
      .replace(/```[\s\S]*?```/g, "")            // 移除代码块
      .replace(/#{1,6}\s+/g, "")                 // 移除标题标记
      .replace(/^\s*[-*+]\s/gm, "· ")            // 列表标记
      .replace(/^\s*\d+\.\s/gm, "· ")            // 有序列表
      .replace(/^\s*>/gm, "")                    // 移除引用
      .replace(/\[([^\]]+)\]\([^\)]+\)/g, "$1")  // 移除链接，保留文本
      .replace(/!\[([^\]]*)\]\([^\)]+\)/g, "[图片]") // 图片转文本
      .replace(/\n{2,}/g, "\n\n");              // 规范化换行
  }
}
```

### 4.3 卡片转换器

```typescript
/**
 * 卡片转换器
 */
class CardConverter {
  /**
   * 转换为钉钉 ActionCard
   */
  static toDingtalk(card: CardBody): Record<string, any> {
    if (card.card_type === "single") {
      const singleAction = card.actions?.[0];
      return {
        msgtype: "actionCard",
        actionCard: {
          title: card.elements.find(e => e.type === "title")?.text || "",
          text: card.elements
            .filter(e => e.type === "text" || e.type === "div")
            .map(e => (e as any).text)
            .join("\n"),
          hideAvatar: card.config?.hide_avatar || "0",
          btnOrientation: card.config?.btn_orientation || "0",
          singleTitle: singleAction?.text,
          singleURL: singleAction?.url
        }
      };
    } else {
      return {
        msgtype: "actionCard",
        actionCard: {
          title: card.elements.find(e => e.type === "title")?.text || "",
          text: card.elements
            .filter(e => e.type === "text" || e.type === "div")
            .map(e => (e as any).text)
            .join("\n"),
          hideAvatar: card.config?.hide_avatar || "0",
          btnOrientation: card.config?.btn_orientation || "1",
          btns: card.actions?.map(action => ({
            title: action.text,
            actionURL: action.url
          }))
        }
      };
    }
  }
  
  /**
   * 转换为飞书交互卡片
   */
  static toFeishu(card: CardBody): Record<string, any> {
    return {
      msg_type: "card",
      content: JSON.stringify({
        config: {
          wide_screen_mode: card.config?.wide_screen_mode ?? true,
          enable_forward: card.config?.enable_forward ?? true
        },
        elements: card.elements.map(el => this.elementToFeishu(el)),
        actions: card.actions?.map(act => this.actionToFeishu(act))
      })
    };
  }
  
  /**
   * 元素转换
   */
  private static elementToFeishu(element: CardElement): Record<string, any> {
    switch (element.type) {
      case "text":
        return { tag: "plain_text", content: (element as any).text };
      case "div":
        return {
          tag: "div",
          text: {
            tag: "lark_md",
            content: (element as any).text
          }
        };
      case "image":
        return {
          tag: "img",
          img_key: (element as any).image_key
        };
      case "hr":
        return { tag: "hr" };
      case "note":
        return {
          tag: "note",
          elements: [{ tag: "plain_text", content: (element as any).text }]
        };
      default:
        return { tag: "div", text: { tag: "plain_text", content: "" } };
    }
  }
  
  /**
   * 动作转换
   */
  private static actionToFeishu(action: CardAction): Record<string, any> {
    const styleMap: Record<string, string> = {
      primary: "primary",
      danger: "danger",
      default: "default"
    };
    
    return {
      tag: "button",
      text: {
        content: action.text,
        tag: "plain_text"
      },
      type: styleMap[action.style || "default"] || "default",
      url: action.url,
      value: action.value
    };
  }
  
  /**
   * 降级卡片为 Markdown
   */
  static downgrade(card: CardBody): UnifiedMessage {
    const text = card.elements
      .filter(e => e.type === "text" || e.type === "div")
      .map(e => (e as any).text)
      .join("\n\n");
    
    const buttons = card.actions
      ?.map(a => `- [${a.text}](${a.url})`)
      .join("\n");
    
    return {
      metadata: {
        correlation_id: card.actions?.[0]?.value?.correlation_id
      },
      content: {
        type: "markdown",
        body: {
          content: `${text}\n\n${buttons || ""}`.trim()
        }
      }
    };
  }
}
```

### 4.4 @提及转换器

```typescript
/**
 * @提及转换器
 */
class MentionConverter {
  /**
   * 转换为企业微信格式
   */
  static toWeCom(mentions: Mention[]): {
    mentioned_list: string[];
    mentioned_mobile_list: string[];
  } {
    const result = {
      mentioned_list: [] as string[],
      mentioned_mobile_list: [] as string[]
    };
    
    for (const mention of mentions) {
      if (mention.type === "all") {
        result.mentioned_list.push("@all");
        result.mentioned_mobile_list.push("@all");
      } else if (mention.type === "user_id") {
        result.mentioned_list.push(mention.value);
      } else if (mention.type === "mobile") {
        result.mentioned_mobile_list.push(mention.value);
      }
    }
    
    return result;
  }
  
  /**
   * 转换为钉钉格式
   */
  static toDingtalk(mentions: Mention[]): {
    atMobiles: string[];
    atUserIds: string[];
    isAtAll: boolean;
  } {
    const result = {
      atMobiles: [] as string[],
      atUserIds: [] as string[],
      isAtAll: false
    };
    
    for (const mention of mentions) {
      if (mention.type === "all") {
        result.isAtAll = true;
      } else if (mention.type === "user_id") {
        result.atUserIds.push(mention.value);
      } else if (mention.type === "mobile") {
        result.atMobiles.push(mention.value);
      }
    }
    
    return result;
  }
  
  /**
   * 转换为飞书格式
   */
  static toFeishu(mentions: Mention[]): string {
    const parts: string[] = [];
    
    for (const mention of mentions) {
      if (mention.type === "all") {
        parts.push("<at id=all></at>");
      } else if (mention.type === "user_id") {
        parts.push(`<at id='${mention.value}'></at>`);
      }
    }
    
    return parts.join(" ");
  }
  
  /**
   * 降级为纯文本
   */
  static downgrade(mentions: Mention[]): string {
    return mentions
      .map(m => m.display_name || m.value)
      .join(", ");
  }
}
```

---

## 5. 消息发送器

### 5.1 发送器接口

```typescript
/**
 * 消息发送器
 */
interface MessageSender {
  // 发送单条消息
  send(message: UnifiedMessage, platform: string): Promise<SendResult>;
  
  // 发送消息到多个平台
  sendMulti(message: UnifiedMessage, platforms: string[]): Promise<MultiSendResult>;
  
  // 发送消息（自动选择可用平台）
  sendAuto(message: UnifiedMessage): Promise<AutoSendResult>;
}

/**
 * 多平台发送结果
 */
interface MultiSendResult {
  // 总数
  total: number;
  
  // 成功数
  success_count: number;
  
  // 失败数
  failed_count: number;
  
  // 结果详情
  results: Array<{
    platform: string;
    success: boolean;
    message_id?: string;
    error?: PlatformError;
  }>;
}

/**
 * 自动发送结果
 */
interface AutoSendResult {
  // 发送成功的平台
  sent_platforms: string[];
  
  // 发送失败或不支持的平台
  skipped_platforms: string[];
  
  // 结果详情
  results: Record<string, SendResult>;
}
```

### 5.2 发送器实现

```typescript
/**
 * 消息发送器实现
 */
class MessageSenderImpl implements MessageSender {
  private registry: AdapterRegistry;
  private httpClient: HTTPClient;
  private retryPolicy: RetryPolicy;
  
  constructor(options: SenderOptions = {}) {
    this.registry = adapterRegistry;
    this.httpClient = options.httpClient || new DefaultHTTPClient();
    this.retryPolicy = options.retryPolicy || DEFAULT_RETRY_POLICY;
  }
  
  async send(message: UnifiedMessage, platform: string): Promise<SendResult> {
    const adapter = this.registry.get(platform);
    
    if (!adapter) {
      return {
        success: false,
        error: {
          code: "UNKNOWN_PLATFORM",
          message: `Unknown platform: ${platform}`
        }
      };
    }
    
    // 检查支持级别
    const supportLevel = adapter.supports(message);
    
    if (supportLevel === SupportLevel.NONE) {
      // 尝试降级
      const downgraded = this.downgradeMessage(message);
      if (downgraded) {
        return this.send(downgraded, platform);
      }
      
      return {
        success: false,
        error: {
          code: "UNSUPPORTED",
          message: `Platform ${platform} does not support this message type`
        }
      };
    }
    
    // 转换消息
    const payload = adapter.transform(message);
    
    // 检查速率限制
    const rateLimit = adapter.getRateLimitInfo();
    if (rateLimit.remaining <= 0) {
      return {
        success: false,
        error: {
          code: "RATE_LIMIT",
          message: "Rate limit exceeded"
        },
        retry_suggested: true
      };
    }
    
    // 发送请求（带重试）
    return this.sendWithRetry(adapter, payload);
  }
  
  async sendMulti(
    message: UnifiedMessage,
    platforms: string[]
  ): Promise<MultiSendResult> {
    const results = await Promise.all(
      platforms.map(platform => this.send(message, platform))
    );
    
    return {
      total: platforms.length,
      success_count: results.filter(r => r.success).length,
      failed_count: results.filter(r => !r.success).length,
      results: results.map((result, index) => ({
        platform: platforms[index],
        success: result.success,
        message_id: result.message_id,
        error: result.error
      }))
    };
  }
  
  async sendAuto(message: UnifiedMessage): Promise<AutoSendResult> {
    const availableAdapters = this.registry.canSend(message);
    
    const results: Record<string, SendResult> = {};
    const sent_platforms: string[] = [];
    const skipped_platforms: string[] = [];
    
    for (const adapter of availableAdapters) {
      const result = await this.send(message, adapter.platform);
      
      results[adapter.platform] = result;
      
      if (result.success) {
        sent_platforms.push(adapter.platform);
      } else if (result.retry_suggested) {
        // 暂时失败，等待重试后可能成功
        sent_platforms.push(adapter.platform);
      } else {
        skipped_platforms.push(adapter.platform);
      }
    }
    
    return {
      sent_platforms,
      skipped_platforms,
      results
    };
  }
  
  /**
   * 降级消息
   */
  private downgradeMessage(message: UnifiedMessage): UnifiedMessage | null {
    switch (message.content.type) {
      case "card":
        return CardConverter.downgrade(message.content.body as CardBody);
      
      case "markdown":
        return {
          ...message,
          content: {
            ...message.content,
            body: {
              content: MarkdownConverter.downgrade(
                (message.content.body as MarkdownBody).content
              )
            }
          }
        };
      
      default:
        return null;
    }
  }
  
  /**
   * 带重试的发送
   */
  private async sendWithRetry(
    adapter: PlatformAdapter,
    payload: PlatformPayload
  ): Promise<SendResult> {
    let lastResult: SendResult | null = null;
    
    for (let attempt = 0; attempt <= this.retryPolicy.max_retries; attempt++) {
      try {
        const response = await this.httpClient.post(
          adapter.getWebhookUrl(),
          payload.body,
          { headers: payload.headers }
        );
        
        lastResult = adapter.parseResponse(response);
        
        if (lastResult.success) {
          return lastResult;
        }
        
        // 如果需要重试
        if (lastResult.retry_suggested && attempt < this.retryPolicy.max_retries) {
          await this.delay(this.getBackoffDelay(attempt));
          continue;
        }
        
        return lastResult;
      } catch (error) {
        if (attempt < this.retryPolicy.max_retries) {
          await this.delay(this.getBackoffDelay(attempt));
        } else {
          return {
            success: false,
            error: {
              code: "NETWORK_ERROR",
              message: error.message
            },
            retry_suggested: false
          };
        }
      }
    }
    
    return lastResult!;
  }
  
  /**
   * 计算退避延迟
   */
  private getBackoffDelay(attempt: number): number {
    const delay = this.retryPolicy.initial_delay * 
      Math.pow(this.retryPolicy.backoff_multiplier, attempt);
    return Math.min(delay, this.retryPolicy.max_delay);
  }
  
  /**
   * 延迟
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}
```

---

## 6. 平台特定实现

### 6.1 企业微信适配器

```typescript
/**
 * 企业微信适配器
 */
class WeComAdapter implements PlatformAdapter {
  readonly platform = "wecom";
  readonly priority = 1;
  
  private webhookUrl: string;
  
  constructor(config: WeComConfig) {
    this.webhookUrl = `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=${config.webhook_key}`;
  }
  
  isAvailable(): boolean {
    return !!this.webhookUrl;
  }
  
  supports(message: UnifiedMessage): SupportLevel {
    const type = message.content.type;
    
    // 完全支持
    if (["text", "markdown", "image", "news", "file", "voice"].includes(type)) {
      return SupportLevel.FULL;
    }
    
    // 卡片部分支持
    if (type === "card") {
      return SupportLevel.PARTIAL;
    }
    
    return SupportLevel.NONE;
  }
  
  transform(message: UnifiedMessage): PlatformPayload {
    const body: Record<string, any> = { msgtype: message.content.type };
    const warnings: string[] = [];
    
    switch (message.content.type) {
      case "text":
        body.text = {
          content: (message.content.body as TextBody).text,
          ...MentionConverter.toWeCom(message.content.mentions || [])
        };
        break;
        
      case "markdown":
        const mdBody = message.content.body as MarkdownBody;
        const markdown = mdBody.enhanced 
          ? MarkdownConverter.convert(mdBody.content, "wecom_v2")
          : MarkdownConverter.convert(mdBody.content, "wecom_standard");
        
        body.markdown = { content: markdown.converted };
        warnings.push(...markdown.warnings);
        break;
        
      case "image":
        body.image = {
          base64: (message.content.body as ImageBody).base64,
          md5: (message.content.body as ImageBody).md5
        };
        break;
        
      case "news":
        body.news = {
          articles: (message.content.body as FeedBody).links.map(link => ({
            title: link.title,
            description: link.title,
            url: link.url,
            picurl: link.image_url
          }))
        };
        break;
        
      case "card":
        // 简化处理
        body.template_card = this.transformCard(message.content.body as CardBody);
        warnings.push("卡片功能部分支持，部分样式可能丢失");
        break;
    }
    
    return { body, warnings };
  }
  
  private transformCard(card: CardBody): Record<string, any> {
    // 转换为模板卡片格式
    return {
      card_type: "text_notice",
      main_title: {
        title: card.elements.find(e => e.type === "title")?.text || ""
      },
      text: card.elements
        .filter(e => e.type === "text" || e.type === "div")
        .map(e => (e as any).text)
        .join("\n")
    };
  }
  
  parseResponse(response: PlatformResponse): SendResult {
    const body = response.body;
    
    return {
      success: body.errcode === 0,
      message_id: body.message_id,
      error: body.errcode !== 0 ? {
        code: body.errcode,
        message: body.errmsg
      } : undefined,
      retry_suggested: body.errcode === 60008 // 频率限制
    };
  }
  
  getRateLimitInfo(): RateLimitInfo {
    return {
      max_requests: 20,
      window_seconds: 60,
      remaining: 20 // 简化处理，实际应从响应头获取
    };
  }
  
  getWebhookUrl(): string {
    return this.webhookUrl;
  }
}

// 注册适配器
adapterRegistry.register(new WeComAdapter({ webhook_key: process.env.WECOM_WEBHOOK_KEY! }));
```

### 6.2 钉钉适配器

```typescript
/**
 * 钉钉适配器
 */
class DingTalkAdapter implements PlatformAdapter {
  readonly platform = "dingtalk";
  readonly priority = 2;
  
  private accessToken: string;
  private secret?: string;
  
  constructor(config: DingTalkConfig) {
    this.accessToken = config.access_token;
    this.secret = config.secret;
  }
  
  isAvailable(): boolean {
    return !!this.accessToken;
  }
  
  supports(message: UnifiedMessage): SupportLevel {
    const type = message.content.type;
    
    // 完全支持
    if (["text", "markdown", "link", "actionCard", "feedCard"].includes(type)) {
      return SupportLevel.FULL;
    }
    
    // 图片、文件、语音、视频不支持（Webhook 方式）
    if (["image", "file", "voice"].includes(type)) {
      return SupportLevel.NONE;
    }
    
    return SupportLevel.NONE;
  }
  
  transform(message: UnifiedMessage): PlatformPayload {
    const body: Record<string, any> = { msgtype: message.content.type };
    const headers: Record<string, string> = {};
    
    // 添加签名（如果配置了）
    if (this.secret) {
      const { timestamp, sign } = this.generateSign();
      headers["Timestamp"] = timestamp;
      headers["Sign"] = sign;
    }
    
    switch (message.content.type) {
      case "text":
        body.text = {
          content: (message.content.body as TextBody).text
        };
        body.at = MentionConverter.toDingtalk(message.content.mentions || []);
        break;
        
      case "markdown":
        body.markdown = {
          title: message.content.title || "",
          text: MarkdownConverter.convert(
            (message.content.body as MarkdownBody).content,
            "dingtalk"
          ).converted
        };
        break;
        
      case "link":
        const link = message.content.body as LinkBody;
        body.link = {
          title: link.title,
          text: link.text || "",
          picUrl: link.image_url || "",
          messageUrl: link.url
        };
        break;
        
      case "actionCard":
        const card = message.content.body as CardBody;
        body.actionCard = CardConverter.toDingtalk(card);
        break;
        
      case "feed":
        body.feedCard = {
          links: (message.content.body as FeedBody).links.map(link => ({
            title: link.title,
            messageURL: link.url,
            picURL: link.image_url
          }))
        };
        break;
    }
    
    // 添加消息去重 ID
    if (message.metadata.message_id) {
      body.msgUuid = message.metadata.message_id;
    }
    
    return { body, headers };
  }
  
  private generateSign(): { timestamp: string; sign: string } {
    const timestamp = Date.now().toString();
    const stringToSign = `${timestamp}\n${this.secret}`;
    
    const sign = crypto
      .createHmac("sha256", this.secret!)
      .update(stringToSign)
      .digest("base64");
    
    return { timestamp, sign };
  }
  
  parseResponse(response: PlatformResponse): SendResult {
    const body = response.body;
    
    return {
      success: body.errcode === 0,
      error: body.errcode !== 0 ? {
        code: body.errcode,
        message: body.errmsg
      } : undefined,
      retry_suggested: body.errcode === 30001 // 频率限制
    };
  }
  
  getRateLimitInfo(): RateLimitInfo {
    return {
      max_requests: 20,
      window_seconds: 60,
      remaining: 20
    };
  }
  
  getWebhookUrl(): string {
    return `https://oapi.dingtalk.com/robot/send?access_token=${this.accessToken}`;
  }
}

// 注册适配器
adapterRegistry.register(new DingTalkAdapter({
  access_token: process.env.DINGTALK_ACCESS_TOKEN!,
  secret: process.env.DINGTALK_SECRET
}));
```

### 6.3 飞书适配器

```typescript
/**
 * 飞书适配器
 */
class FeishuAdapter implements PlatformAdapter {
  readonly platform = "feishu";
  readonly priority = 3;
  
  private webhookId: string;
  
  constructor(config: FeishuConfig) {
    this.webhookId = config.webhook_id;
  }
  
  isAvailable(): boolean {
    return !!this.webhookId;
  }
  
  supports(message: UnifiedMessage): SupportLevel {
    const type = message.content.type;
    
    // V2 Webhook 完全支持
    if (["text", "post", "image", "file", "card", "audio"].includes(type)) {
      return SupportLevel.FULL;
    }
    
    return SupportLevel.NONE;
  }
  
  transform(message: UnifiedMessage): PlatformPayload {
    const body: Record<string, any> = {};
    const warnings: string[] = [];
    
    switch (message.content.type) {
      case "text":
        body.msg_type = "text";
        body.content = {
          text: this.processMentions(
            (message.content.body as TextBody).text,
            message.content.mentions || []
          )
        };
        break;
        
      case "post":
        body.msg_type = "post";
        body.content = JSON.stringify({
          post: {
            zh_cn: {
              title: message.content.title || "",
              content: [this.parseMarkdownToRichText(
                (message.content.body as MarkdownBody).content
              )]
            }
          }
        });
        break;
        
      case "image":
        body.msg_type = "image";
        body.content = {
          image_key: (message.content.body as ImageBody).image_key
        };
        break;
        
      case "card":
        body.msg_type = "card";
        body.content = JSON.stringify(
          CardConverter.toFeishu(message.content.body as CardBody)
        );
        break;
        
      case "file":
        body.msg_type = "file";
        body.content = {
          file_key: (message.content.body as FileBody).media_id,
          file_name: (message.content.body as FileBody).file_name
        };
        break;
    }
    
    return { body, warnings };
  }
  
  private processMentions(text: string, mentions: Mention[]): string {
    for (const mention of mentions) {
      if (mention.type === "all") {
        text = `<at id=all></at> ${text}`;
      } else if (mention.type === "user_id") {
        text = text.replace(
          mention.display_name || mention.value,
          `<at id='${mention.value}'></at>`
        );
      }
    }
    return text;
  }
  
  private parseMarkdownToRichText(markdown: string): any[] {
    // 简化实现：将 Markdown 转换为飞书富文本格式
    return [
      {
        type: "text",
        text: MarkdownConverter.downgrade(markdown)
      }
    ];
  }
  
  parseResponse(response: PlatformResponse): SendResult {
    const body = response.body;
    
    return {
      success: body.code === 0,
      error: body.code !== 0 ? {
        code: body.code,
        message: body.msg
      } : undefined,
      retry_suggested: [216429, 216629].includes(body.code)
    };
  }
  
  getRateLimitInfo(): RateLimitInfo {
    return {
      max_requests: 100,
      window_seconds: 60,
      remaining: 100
    };
  }
  
  getWebhookUrl(): string {
    return `https://open.feishu.cn/open-apis/bot/v2/hook/${this.webhookId}`;
  }
}

// 注册适配器
adapterRegistry.register(new FeishuAdapter({
  webhook_id: process.env.FEISHU_WEBHOOK_ID!
}));
```

---

## 7. 使用示例

### 7.1 基本使用

```typescript
/**
 * 发送文本消息
 */
async function sendTextMessage() {
  const sender = new MessageSenderImpl();
  
  const message: UnifiedMessage = {
    metadata: {
      message_id: "msg_001",
      priority: "normal"
    },
    content: {
      type: "text",
      title: "通知",
      body: {
        text: "这是一条测试消息"
      },
      mentions: [
        { type: "mobile", value: "13800000000", display_name: "张三" }
      ]
    }
  };
  
  // 发送到指定平台
  const result = await sender.send(message, "dingtalk");
  console.log(result);
  
  // 发送到多个平台
  const multiResult = await sender.sendMulti(message, ["wecom", "dingtalk"]);
  console.log(multiResult);
  
  // 自动选择可用平台
  const autoResult = await sender.sendAuto(message);
  console.log(autoResult);
}
```

### 7.2 发送 Markdown 消息

```typescript
/**
 * 发送 Markdown 报告
 */
async function sendMarkdownReport() {
  const sender = new MessageSenderImpl();
  
  const message: UnifiedMessage = {
    metadata: {
      message_id: "report_001",
      priority: "normal"
    },
    content: {
      type: "markdown",
      title: "每日数据报告",
      body: {
        content: `# 今日数据概览

## 核心指标
- **新增用户**: 128
- *活跃用户*: 3,421
- 转化率: 5.2%

> 数据更新时间: 2024-01-01 18:00`
      }
    }
  };
  
  // 自动发送到所有可用平台
  const result = await sender.sendAuto(message);
  
  console.log(`成功发送到: ${result.sent_platforms.join(", ")}`);
  console.log(`跳过平台: ${result.skipped_platforms.join(", ")}`);
}
```

### 7.3 发送卡片消息

```typescript
/**
 * 发送告警卡片
 */
async function sendAlertCard() {
  const sender = new MessageSenderImpl();
  
  const message: UnifiedMessage = {
    metadata: {
      message_id: "alert_001",
      priority: "high"
    },
    content: {
      type: "card",
      body: {
        card_type: "interactive",
        config: {
          wide_screen_mode: true
        },
        elements: [
          {
            type: "div",
            text: "**🔴 服务器告警**\n\nCPU 使用率超过 90%"
          },
          {
            type: "div",
            text: "服务器：web-01\n当前 CPU：95%"
          }
        ],
        actions: [
          {
            type: "button",
            text: "查看详情",
            url: "https://example.com/alerts/123",
            value: { alert_id: "123" },
            style: "primary"
          },
          {
            type: "button",
            text: "忽略",
            url: "https://example.com/alerts/123/dismiss",
            value: { action: "dismiss" }
          }
        ]
      }
    }
  };
  
  // 发送到钉钉
  const result = await sender.send(message, "dingtalk");
  
  if (result.success) {
    console.log(`卡片发送成功，消息ID: ${result.message_id}`);
  } else {
    console.error(`发送失败: ${result.error?.message}`);
    
    // 降级为 Markdown 发送
    if (result.error?.code === "UNSUPPORTED") {
      const downgraded = CardConverter.downgrade(message.content.body as CardBody);
      await sender.send(downgraded, "dingtalk");
    }
  }
}
```

### 7.4 批量发送

```typescript
/**
 * 批量发送消息到多个平台
 */
async function sendBatchMessages() {
  const sender = new MessageSenderImpl();
  
  const platforms = ["wecom", "dingtalk", "feishu"];
  
  const messages: UnifiedMessage[] = [
    {
      content: {
        type: "text",
        body: { text: "企业微信通知" }
      }
    },
    {
      content: {
        type: "text",
        body: { text: "钉钉通知" }
      }
    },
    {
      content: {
        type: "text",
        body: { text: "飞书通知" }
      }
    }
  ];
  
  // 并行发送
  const results = await Promise.all(
    messages.map(msg => sender.sendMulti(msg, platforms))
  );
  
  // 汇总结果
  let totalSuccess = 0;
  let totalFailed = 0;
  
  for (const result of results) {
    totalSuccess += result.success_count;
    totalFailed += result.failed_count;
  }
  
  console.log(`总发送: ${messages.length * platforms.length}`);
  console.log(`成功: ${totalSuccess}`);
  console.log(`失败: ${totalFailed}`);
}
```

### 7.5 带重试的发送

```typescript
/**
 * 带自定义重试策略的发送
 */
async function sendWithRetry() {
  const sender = new MessageSenderImpl({
    retryPolicy: {
      max_retries: 5,
      initial_delay: 1000,
      max_delay: 30000,
      backoff_multiplier: 2
    }
  });
  
  const message: UnifiedMessage = {
    content: {
      type: "text",
      body: { text: "重要通知" }
    }
  };
  
  try {
    const result = await sender.send(message, "dingtalk");
    
    if (result.success) {
      console.log("发送成功");
    } else {
      console.log(`发送失败: ${result.error?.message}`);
    }
  } catch (error) {
    console.error("发送异常:", error);
  }
}
```

---

## 8. 最佳实践

### 8.1 消息设计建议

1. **优先使用 Markdown**
   - Markdown 是三个平台都支持的格式
   - 可读性好，易于维护
   - 支持降级为纯文本

2. **卡片消息降级策略**
   ```typescript
   // 优先发送卡片
   if (platformSupportsCard(platform)) {
     return sendCard();
   }
   
   // 降级为 Markdown + 链接
   return sendMarkdownWithButtons();
   ```

3. **@提及处理**
   ```typescript
   // 优先使用 user_id（最准确）
   // 次之使用 mobile（钉钉支持）
   // 最后使用 @all（谨慎使用）
   ```

4. **错误处理**
   ```typescript
   async function safeSend(message: UnifiedMessage, platform: string) {
     try {
       return await sender.send(message, platform);
     } catch (error) {
       // 记录错误
       logger.error(`Failed to send to ${platform}`, error);
       
       // 返回降级结果
       return {
         success: false,
         error: { code: "SEND_FAILED", message: error.message },
         retry_suggested: true
       };
     }
   }
   ```

### 8.2 性能优化

1. **连接池**
   ```typescript
   const sender = new MessageSenderImpl({
     httpClient: new HTTPClient({
       maxConnections: 10,
       keepAlive: true
     })
   });
   ```

2. **批量发送**
   ```typescript
   // 使用 Promise.all 并行发送
   const results = await Promise.all(
     platforms.map(p => sender.send(message, p))
   );
   ```

3. **缓存 Webhook URL**
   ```typescript
   // 避免每次发送都解析 URL
   const adapter = registry.get(platform);
   const url = adapter.getWebhookUrl(); // 缓存此 URL
   ```

### 8.3 监控和日志

```typescript
class MonitoredSender implements MessageSender {
  async send(message: UnifiedMessage, platform: string): Promise<SendResult> {
    const startTime = Date.now();
    
    // 记录发送尝试
    logger.info("Sending message", {
      message_id: message.metadata.message_id,
      platform,
      type: message.content.type
    });
    
    const result = await this.innerSender.send(message, platform);
    
    // 记录发送结果
    logger.info("Message sent", {
      message_id: message.metadata.message_id,
      platform,
      success: result.success,
      duration: Date.now() - startTime,
      error: result.error?.code
    });
    
    // 发送失败时告警
    if (!result.success && result.retry_suggested) {
      alertManager.sendAlert({
        type: "MESSAGE_SEND_FAILED",
        platform,
        message_id: message.metadata.message_id
      });
    }
    
    return result;
  }
}
```

---

## 9. 总结

本文档定义了 `webhook-push` 技能的通用消息设计方案，通过以下关键设计实现跨平台消息发送：

| 设计要点 | 实现方式 |
|---------|---------|
| **统一消息模型** | `UnifiedMessage` 接口，屏蔽平台差异 |
| **平台适配器** | `PlatformAdapter` 接口，支持热插拔 |
| **消息转换器** | `MessageConverter` 接口，处理格式转换 |
| **渐进式降级** | 卡片 → Markdown → 纯文本 |
| **错误处理** | 统一错误码，自动重试 |
| **速率限制** | 平台级限流控制 |

**后续扩展**：

1. 添加更多平台支持（Slack、Microsoft Teams 等）
2. 支持消息模板
3. 支持消息撤回
4. 支持消息状态查询
5. 添加消息统计和分析

---

*文档版本：1.0*  
*最后更新：2025 年 1 月*  
*作者：Webhook Push Skill 设计团队*
