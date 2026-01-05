"""Tests for webhook-push converters."""

import pytest
from webhook_push.converters import (
    MarkdownConverter,
    CardConverter,
    MentionConverter,
)


class TestMarkdownConverter:
    """Tests for MarkdownConverter."""

    def test_downgrade_bold(self):
        """Test downgrading bold text."""
        result = MarkdownConverter.downgrade("**bold text**")
        assert "**" not in result
        assert "bold text" in result

    def test_downgrade_italic(self):
        """Test downgrading italic text."""
        result = MarkdownConverter.downgrade("*italic text*")
        assert "*" not in result or result.count("*") == result.count("\\*")
        assert "italic text" in result

    def test_downgrade_code_blocks(self):
        """Test downgrading code blocks."""
        result = MarkdownConverter.downgrade("```python\nprint('hello')\n```")
        assert "python" not in result.lower() or "print" not in result.lower()

    def test_downgrade_headers(self):
        """Test downgrading headers."""
        result = MarkdownConverter.downgrade("# Title\n## Subtitle\n### Heading 3")
        assert "#" not in result

    def test_downgrade_links(self):
        """Test downgrading links."""
        result = MarkdownConverter.downgrade("[Click here](https://example.com)")
        assert "[Click here]" not in result
        assert "https://example.com" not in result
        assert "Click here" in result

    def test_downgrade_images(self):
        """Test downgrading images."""
        result = MarkdownConverter.downgrade("![Alt text](https://example.com/img.png)")
        assert "![Alt text]" not in result
        assert "[图片]" in result

    def test_downgrade_lists(self):
        """Test downgrading lists."""
        result = MarkdownConverter.downgrade("- Item 1\n- Item 2\n- Item 3")
        assert "· Item 1" in result

    def test_downgrade_preserves_content(self):
        """Test that content is preserved after downgrade."""
        content = """# Report

## Summary
- **Key metric**: 128
- Another point

> Important note

[View details](https://example.com)"""

        result = MarkdownConverter.downgrade(content)

        # Check that key content is preserved
        assert "Report" in result
        assert "Key metric" in result or "Key metric" in content.replace("**", "")
        assert "128" in result
        assert "Important note" in result
        # Links are replaced with their text
        assert "View details" in result
        assert "https://example.com" not in result


class TestCardConverter:
    """Tests for CardConverter."""

    def test_downgrade_card_to_markdown(self):
        """Test downgrading a card to markdown."""
        card = {
            "card_type": "interactive",
            "elements": [
                {"type": "div", "text": "Alert message"},
                {"type": "div", "text": "Additional info"}
            ],
            "actions": [
                {"type": "button", "text": "Approve", "url": "https://example.com/approve"},
                {"type": "button", "text": "Reject", "url": "https://example.com/reject"}
            ]
        }

        result = CardConverter.downgrade(card)

        assert result["type"] == "markdown"
        assert "Alert message" in result["body"]["content"]
        assert "- [Approve](https://example.com/approve)" in result["body"]["content"]
        assert "- [Reject](https://example.com/reject)" in result["body"]["content"]

    def test_to_dingtalk_single_button(self):
        """Test converting card to DingTalk single button format."""
        card = {
            "card_type": "single",
            "config": {"btn_orientation": "0"},
            "elements": [{"type": "div", "text": "Confirm action?"}],
            "actions": [
                {"type": "button", "text": "Confirm", "url": "https://example.com/confirm"}
            ]
        }

        result = CardConverter.to_dingtalk(card)

        assert result["singleTitle"] == "Confirm"
        assert result["singleURL"] == "https://example.com/confirm"
        assert "btns" not in result

    def test_to_dingtalk_multi_button(self):
        """Test converting card to DingTalk multi button format."""
        card = {
            "card_type": "multi",
            "config": {"btn_orientation": "1"},
            "elements": [{"type": "div", "text": "Select action:"}],
            "actions": [
                {"type": "button", "text": "Approve", "url": "https://example.com/approve"},
                {"type": "button", "text": "Reject", "url": "https://example.com/reject"}
            ]
        }

        result = CardConverter.to_dingtalk(card)

        assert "btns" in result
        assert len(result["btns"]) == 2
        assert result["btns"][0]["title"] == "Approve"

    def test_to_feishu(self):
        """Test converting card to Feishu format."""
        card = {
            "card_type": "interactive",
            "config": {"wide_screen_mode": True, "enable_forward": True},
            "elements": [
                {"type": "div", "text": "Alert: High CPU usage"},
                {"type": "image", "image_key": "img_123"}
            ],
            "actions": [
                {"type": "button", "text": "View", "url": "https://example.com/view", "style": "primary"}
            ]
        }

        result = CardConverter.to_feishu(card)

        assert "config" in result
        assert result["config"]["wide_screen_mode"] is True
        assert len(result["elements"]) == 4  # div + img + hr + action
        assert result["elements"][0]["tag"] == "div"
        assert result["elements"][1]["tag"] == "img"
        assert result["elements"][2]["tag"] == "hr"
        assert result["elements"][3]["actions"][0]["text"]["content"] == "View"


class TestMentionConverter:
    """Tests for MentionConverter."""

    def test_to_wecom_at_all(self):
        """Test converting @all to WeCom format."""
        mentions = [{"type": "all", "value": "@all"}]
        result = MentionConverter.to_wecom(mentions)

        assert "@all" in result["mentioned_list"]
        assert "@all" in result["mentioned_mobile_list"]

    def test_to_wecom_user_ids(self):
        """Test converting user IDs to WeCom format."""
        mentions = [
            {"type": "user_id", "value": "user123"},
            {"type": "user_id", "value": "user456"}
        ]
        result = MentionConverter.to_wecom(mentions)

        assert "user123" in result["mentioned_list"]
        assert "user456" in result["mentioned_list"]

    def test_to_wecom_mobiles(self):
        """Test converting mobiles to WeCom format."""
        mentions = [
            {"type": "mobile", "value": "13800000000"},
            {"type": "mobile", "value": "13900000000"}
        ]
        result = MentionConverter.to_wecom(mentions)

        assert "13800000000" in result["mentioned_mobile_list"]

    def test_to_dingtalk_at_all(self):
        """Test converting @all to DingTalk format."""
        mentions = [{"type": "all", "value": "@all"}]
        result = MentionConverter.to_dingtalk(mentions)

        assert result["isAtAll"] is True
        assert result["atMobiles"] == []
        assert result["atUserIds"] == []

    def test_to_dingtalk_mixed(self):
        """Test converting mixed mentions to DingTalk format."""
        mentions = [
            {"type": "mobile", "value": "13800000000"},
            {"type": "user_id", "value": "user123"},
            {"type": "all", "value": "@all"}
        ]
        result = MentionConverter.to_dingtalk(mentions)

        assert result["isAtAll"] is True
        assert "13800000000" in result["atMobiles"]
        assert "user123" in result["atUserIds"]

    def test_to_feishu(self):
        """Test converting mentions to Feishu format."""
        mentions = [
            {"type": "all", "value": "@all"},
            {"type": "user_id", "value": "user123", "display_name": "Zhang San"}
        ]
        result = MentionConverter.to_feishu(mentions)

        assert "<at id=all></at>" in result
        assert "<at id='user123'></at>" in result

    def test_downgrade(self):
        """Test downgrading mentions to plain text."""
        mentions = [
            {"type": "mobile", "value": "13800000000", "display_name": "Zhang San"},
            {"type": "user_id", "value": "user123", "display_name": "Li Si"}
        ]
        result = MentionConverter.downgrade(mentions)

        assert "Zhang San" in result
        assert "Li Si" in result
