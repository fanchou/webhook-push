"""Configuration management for webhook-push skill."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import ValidationError

from .models import PlatformConfig, WebhookPushConfig


class ConfigLoader:
    """Load and manage webhook-push configuration."""

    # Default config file locations
    DEFAULT_CONFIG_PATHS = [
        "webhook-push.yaml",
        "webhook-push.yml",
        "~/.webhook-push.yaml",
        "~/.webhook-push.yml",
    ]

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> WebhookPushConfig:
        """Load configuration from file.

        Args:
            config_path: Path to config file. If None, searches default locations.

        Returns:
            WebhookPushConfig instance

        Raises:
            FileNotFoundError: If no config file found
            ValidationError: If config is invalid
        """
        config_file = cls._find_config_file(config_path)

        if not config_file:
            raise FileNotFoundError(
                "Config file not found. Please create webhook-push.yaml "
                "or specify a path with --config option."
            )

        with open(config_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            return WebhookPushConfig()

        return cls._parse_config(data)

    @classmethod
    def _find_config_file(cls, config_path: Optional[str] = None) -> Optional[Path]:
        """Find configuration file.

        Args:
            config_path: Specific path to check first

        Returns:
            Path to config file or None
        """
        # Check specific path first
        if config_path:
            path = Path(config_path).expanduser()
            if path.exists():
                return path

        # Check default locations
        for location in cls.DEFAULT_CONFIG_PATHS:
            path = Path(location).expanduser()
            if path.exists():
                return path

        return None

    @classmethod
    def _parse_config(cls, data: dict) -> WebhookPushConfig:
        """Parse configuration data.

        Args:
            data: Raw configuration dict

        Returns:
            Parsed WebhookPushConfig

        Raises:
            ValidationError: If config is invalid
        """
        # Parse platforms
        platforms: dict[str, PlatformConfig] = {}

        for platform_name, platform_data in data.get("platforms", {}).items():
            if not isinstance(platform_data, dict):
                continue

            webhook_url = platform_data.get("webhook_url", "")
            secret = platform_data.get("secret")
            enabled = platform_data.get("enabled", True)

            # Also check environment variables
            env_prefix = platform_name.upper()
            if not webhook_url:
                webhook_url = os.getenv(f"{env_prefix}_WEBHOOK_URL", "")
            if not secret:
                secret = os.getenv(f"{env_prefix}_SECRET")

            platforms[platform_name] = PlatformConfig(
                webhook_url=webhook_url,
                secret=secret,
                enabled=enabled
            )

        # Parse retry policy
        retry_data = data.get("retry", {})
        retry_policy = {
            "max_retries": retry_data.get("max_retries", 3),
            "initial_delay": retry_data.get("initial_delay", 1000),
            "max_delay": retry_data.get("max_delay", 30000),
            "backoff_multiplier": retry_data.get("backoff_multiplier", 2.0),
        }

        # Parse default timeout
        default_timeout = data.get("default_timeout", 5000)

        return WebhookPushConfig(
            platforms=platforms,
            retry=retry_policy,
            default_timeout=default_timeout
        )

    @classmethod
    def load_or_create(cls) -> WebhookPushConfig:
        """Load existing config or create default.

        Returns:
            WebhookPushConfig instance (may be empty default)
        """
        try:
            return cls.load()
        except FileNotFoundError:
            return WebhookPushConfig()


def load_config(config_path: Optional[str] = None) -> WebhookPushConfig:
    """Convenience function to load configuration.

    Args:
        config_path: Optional path to config file

    Returns:
        WebhookPushConfig instance
    """
    return ConfigLoader.load(config_path)
