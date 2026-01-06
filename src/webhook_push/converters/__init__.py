"""Message converters for webhook-push skill.

This module provides converters for transforming messages between different
formats and platforms.
"""

from __future__ import annotations

import re
from typing import Any, Optional


class MarkdownConverter:
    """Converter for Markdown content across platforms."""

    # Syntax mapping for different platforms
    SYNTAX_MAP: dict[str, dict[str, str]] = {
        "wecom_standard": {
            "bold": r"**(.+?)**",
            "color": r'<font color="(info|comment|warning)">(.+?)</font>',
        },
        "wecom_v2": {
            "bold": r"**(.+?)**",
            "italic": r"*(.+?)*",
            "table": r"\|(.+)\|",
        },
        "dingtalk": {
            "bold": r"**(.+?)**",
            "italic": r"*(.+?)*",
        },
        "feishu": {
            "bold": r"\*\*(.+?)\*\*",
            "italic": r"\*(.+?)\*",
        },
    }

    @staticmethod
    def convert(content: str, platform: str) -> tuple[str, list[str]]:
        """Convert Markdown content to platform-specific format.

        Args:
            content: Source Markdown content
            platform: Target platform (wecom_standard, wecom_v2, dingtalk, feishu)

        Returns:
            Tuple of (converted content, warnings)
        """
        warnings: list[str] = []
        result = content

        if platform == "wecom_standard":
            # Keep most Markdown as-is for WeCom standard
            pass

        elif platform == "wecom_v2":
            # V2 supports more Markdown features
            pass

        elif platform == "dingtalk":
            # DingTalk supports basic GFM
            # Remove code blocks (not supported)
            result = re.sub(r"```[\s\S]*?```", "", result)

        elif platform == "feishu":
            # Feishu lark_md supports basic Markdown
            pass

        return result, warnings

    @staticmethod
    def downgrade(content: str) -> str:
        """Downgrade Markdown to plain text.

        Args:
            content: Markdown content

        Returns:
            Plain text content
        """
        # Remove formatting
        result = re.sub(r"\*\*(.+?)\*\*", r"\1", content)  # bold
        result = re.sub(r"\*(.+?)\*", r"\1", result)  # italic
        result = re.sub(r"```[\s\S]*?```", "", result)  # code blocks
        result = re.sub(r"`(.+?)`", r"\1", result)  # inline code
        result = re.sub(r"^#{1,6}\s+", "", result, flags=re.MULTILINE)  # headers
        result = re.sub(r"^\s*[-*+]\s", "· ", result, flags=re.MULTILINE)  # bullet lists
        result = re.sub(r"^\s*\d+\.\s", "· ", result, flags=re.MULTILINE)  # numbered lists
        result = re.sub(r"^\s*>", "", result, flags=re.MULTILINE)  # blockquotes
        # images (must be before links)
        result = re.sub(r"!\[([^\]]*)\]\([^\)]+\)", "[图片]", result)
        result = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", result)  # links
        result = re.sub(r"\n{3,}", "\n\n", result)  # normalize newlines

        return result.strip()


class CardConverter:
    """Converter for card messages across platforms."""

    @staticmethod
    def to_dingtalk(card_body: dict[str, Any]) -> dict[str, Any]:
        """Convert card to DingTalk actionCard format."""
        config = card_body.get("config", {})
        actions = card_body.get("actions", [])

        result = {
            "title": "",
            "text": "",
            "hideAvatar": config.get("hide_avatar", "0"),
            "btnOrientation": config.get("btn_orientation", "0")
        }

        # Extract text from elements
        text_parts = []
        for elem in card_body.get("elements", []):
            if elem.get("text"):
                text_parts.append(elem["text"])
        result["text"] = "\n".join(text_parts)

        # Handle buttons
        if len(actions) == 1:
            result["singleTitle"] = actions[0].get("text", "")
            result["singleURL"] = actions[0].get("url", "")
        elif len(actions) > 1:
            result["btns"] = [
                {"title": a.get("text", ""), "actionURL": a.get("url", "")}
                for a in actions
            ]

        return result

    @staticmethod
    def to_feishu(card_body: dict[str, Any]) -> dict[str, Any]:
        """Convert card to Feishu interactive card format."""
        config = card_body.get("config", {})

        card: dict[str, Any] = {
            "config": {
                "wide_screen_mode": config.get("wide_screen_mode", True),
                "enable_forward": config.get("enable_forward", True)
            },
            "elements": []
        }
        elements: list[dict[str, Any]] = []

        # Transform elements
        for elem in card_body.get("elements", []):
            elem_type = elem.get("type", "div")
            if elem_type == "div":
                elements.append({
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": elem.get("text", "")
                    }
                })
            elif elem_type == "image":
                elements.append({
                    "tag": "img",
                    "img_key": elem.get("image_key", "")
                })
            elif elem_type == "hr":
                elements.append({"tag": "hr"})

        # Transform actions
        if card_body.get("actions"):
            elements.append({"tag": "hr"})
            actions_elem: dict[str, Any] = {"tag": "action", "actions": []}
            actions_list: list[dict[str, Any]] = []
            for action in card_body["actions"]:
                action_obj: dict[str, Any] = {
                    "tag": "button",
                    "text": {"content": action.get("text", ""), "tag": "plain_text"},
                    "type": action.get("style", "default")
                }
                if action.get("url"):
                    action_obj["url"] = action["url"]
                actions_list.append(action_obj)
            actions_elem["actions"] = actions_list
            elements.append(actions_elem)

        card["elements"] = elements
        return card

    @staticmethod
    def downgrade(card_body: dict[str, Any]) -> dict[str, Any]:
        """Downgrade card to Markdown format."""
        text_parts = []
        buttons = []

        # Extract text from elements
        for elem in card_body.get("elements", []):
            if elem.get("text"):
                text_parts.append(elem["text"])

        # Extract button text and URLs
        for action in card_body.get("actions", []):
            btn_text = action.get("text", "")
            btn_url = action.get("url", "")
            buttons.append(f"- [{btn_text}]({btn_url})")

        text = "\n\n".join(text_parts)
        button_text = "\n".join(buttons)

        content = f"{text}\n\n{button_text}".strip()

        return {
            "type": "markdown",
            "body": {"content": content}
        }


class MentionConverter:
    """Converter for @mentions across platforms."""

    @staticmethod
    def to_wecom(mentions: list[dict[str, Any]]) -> dict[str, list[str]]:
        """Convert mentions to WeCom format."""
        result: dict[str, list[str]] = {
            "mentioned_list": [],
            "mentioned_mobile_list": []
        }

        for mention in mentions:
            if mention.get("type") == "all":
                result["mentioned_list"].append("@all")
                result["mentioned_mobile_list"].append("@all")
            elif mention.get("type") == "user_id":
                result["mentioned_list"].append(mention.get("value", ""))
            elif mention.get("type") == "mobile":
                result["mentioned_mobile_list"].append(mention.get("value", ""))

        return result

    @staticmethod
    def to_dingtalk(mentions: list[dict[str, Any]]) -> dict[str, Any]:
        """Convert mentions to DingTalk format."""
        result: dict[str, Any] = {
            "atMobiles": [],
            "atUserIds": [],
            "isAtAll": False
        }
        at_mobiles: list[str] = []
        at_user_ids: list[str] = []

        for mention in mentions:
            if mention.get("type") == "all":
                result["isAtAll"] = True
            elif mention.get("type") == "user_id":
                at_user_ids.append(mention.get("value", ""))
            elif mention.get("type") == "mobile":
                at_mobiles.append(mention.get("value", ""))

        result["atUserIds"] = at_user_ids
        result["atMobiles"] = at_mobiles

        return result

    @staticmethod
    def to_feishu(mentions: list[dict[str, Any]]) -> str:
        """Convert mentions to Feishu format."""
        parts = []

        for mention in mentions:
            if mention.get("type") == "all":
                parts.append("<at id=all></at>")
            elif mention.get("type") == "user_id":
                parts.append(f"<at id='{mention.get('value', '')}'></at>")

        return " ".join(parts)

    @staticmethod
    def downgrade(mentions: list[dict[str, Any]]) -> str:
        """Downgrade mentions to plain text."""
        return ", ".join(
            m.get("display_name", m.get("value", ""))
            for m in mentions
        )


class ImageConverter:
    """Converter for image content."""

    @staticmethod
    def validate_image(image_body: dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate image data.

        Args:
            image_body: Image body dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not image_body.get("url") and not image_body.get("base64"):
            return False, "Image must have either url or base64"

        # WeCom requires base64 + md5
        if image_body.get("base64") and not image_body.get("md5"):
            return False, "WeCom images require md5 hash"

        return True, None

    @staticmethod
    def calculate_md5(data: bytes) -> str:
        """Calculate MD5 hash of image data."""
        import hashlib
        return hashlib.md5(data).hexdigest()
