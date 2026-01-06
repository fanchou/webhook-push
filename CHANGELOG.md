# Changelog

All notable changes to the webhook-push skill will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of webhook-push skill
- Unified message model for WeCom, DingTalk, and Feishu platforms
- Support for multiple message types: text, markdown, image, link, card, file, feed
- Platform-specific adapters with automatic message conversion
- Graceful degradation for unsupported features
- Built-in retry mechanism with exponential backoff
- Rate limit handling for all platforms
- CLI tool for sending messages from command line
- Comprehensive test coverage for models and converters
- Type hints and Pydantic validation throughout
- Support for @mentions in text messages
- Multi-platform sending capabilities
- Automatic platform selection based on configuration
- **Feishu Signature Verification**: Added HMAC-SHA256 signature verification support for Feishu webhooks to enhance security
- **Configuration Loader**: Added `ConfigLoader` class for loading configuration from YAML files
- **CLI Config Support**: Added `--config` and `--secret` options to CLI for configuration file and signature support

### Fixed
- **Feishu Message Format**: Fixed critical bug where `post` and `card` message content was incorrectly converted to string instead of keeping as JSON object
- **Feishu Signature Algorithm**: Implemented correct HMAC-SHA256 signature algorithm following official Feishu documentation
- **Feishu Bot Payloads**: Signatures moved into request body (`timestamp` + `sign`), post content uses Feishu `tag` schema, interactive cards output `msg_type=interactive` with `card` payload and pass-through of Feishu-native elements/actions, @all mentions use `<at user_id="all">`
- **Template Card Support**: Added comprehensive WeCom template_card (text_notice, news_show) and DingTalk actionCard support
- **DingTalk Signature**: Fixed signature URL encoding issue (双重编码 bug)
- **WeCom Markdown**: Added auto-detection of tables to use markdown_v2 format
- **Type Safety**: Fixed multiple mypy type errors across adapters, converters, sender, and CLI
- **DingTalk Adapter**: Fixed supports() method to recognize "card" type
- **Response Parsing**: Fixed rate limit error code detection for DingTalk and Feishu
- **Test Coverage**: Fixed failing tests related to PlatformError object handling

### Changed
- **WeCom Markdown**: Now auto-detects tables and uses markdown_v2 automatically
- **DingTalk Signature**: Signature is no longer URL-encoded in adapter (sender handles it)
- **API**: Added WeComTemplateCard, WeComSource, WeComEmphasisContent, WeComQuoteArea, WeComHorizontalContent, WeComJumpList, WeComCardAction models

## [0.1.0] - 2025-01-05

### Added
- Core message models (UnifiedMessage, MessageContent, etc.)
- Platform adapters for WeCom, DingTalk, and Feishu
- Message converters (MarkdownConverter, CardConverter, MentionConverter)
- MessageSender with retry logic
- CLI interface (`webhook-push` command)
- Pydantic-based data validation
- Configuration via environment variables and YAML file
- Comprehensive documentation and examples
- Unit tests for core functionality

### Documentation
- SKILL.md with complete usage guide
- README.md with quick start guide
- Design documents in `references/`
- API reference documentation
- Platform-specific documentation
- Contributing guidelines

---

## Version Format

The version numbers follow this format: `MAJOR.MINOR.PATCH`

- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality (backwards compatible)
- **PATCH**: Bug fixes (backwards compatible)

## Types of Changes

- `Added` - New features
- `Changed` - Changes in existing functionality
- `Deprecated` - Soon-to-be removed features
- `Removed` - Removed features
- `Fixed` - Bug fixes
- `Security` - Security vulnerability fixes
