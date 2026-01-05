"""CLI entry point for webhook-push skill."""

import asyncio
import json
import sys
from typing import IO, Any, Optional

import click

from .adapters import default_registry
from .models import MessageContent, MessageMetadata, UnifiedMessage
from .sender import MessageSender


def build_message(
    msg_type: str,
    content: str,
    title: Optional[str] = None
) -> UnifiedMessage:
    """Build a unified message from command line arguments."""
    body: dict[str, Any] = {"text": content}
    if msg_type == "markdown":
        body = {"content": content}
    elif msg_type == "card":
        body = json.loads(content)

    return UnifiedMessage(
        metadata=MessageMetadata(),
        content=MessageContent(
            type=msg_type,
            title=title,
            body=body
        )
    )


@click.group()
def cli() -> None:
    """Webhook Push CLI - Send messages to enterprise platforms."""


@cli.command()
@click.argument("platform")
@click.argument("webhook_url")
@click.option("--type", "msg_type", default="text", type=click.Choice(["text", "markdown"]))
@click.option("--title", "-t", default=None, help="Message title")
@click.option("--content", "-c", default=None, help="Message content")
@click.option("--file", "-f", type=click.File("r"), help="File containing message content")
@click.option("--json", "json_output", is_flag=True, help="Output result as JSON")
def send(
    platform: str,
    webhook_url: str,
    msg_type: str,
    title: Optional[str],
    content: Optional[str],
    file: Optional[IO[str]],
    json_output: bool
) -> None:
    """Send a message to a specific platform."""
    # Read content from file or argument
    if file:
        actual_content = file.read()
    elif content:
        actual_content = content
    else:
        click.echo("Error: Must provide content via --content or --file", err=True)
        sys.exit(1)

    # Build message
    message = build_message(msg_type, actual_content, title)

    # Create sender and send
    sender = MessageSender()
    result = asyncio.run(sender.send(message, platform, webhook_url))

    # Output result
    if json_output:
        click.echo(json.dumps(result.__dict__, indent=2, ensure_ascii=False))
    elif result.success:
        click.echo(f"✓ Message sent successfully to {platform}")
        if result.message_id:
            click.echo(f"  Message ID: {result.message_id}")
    else:
        click.echo(f"✗ Failed to send to {platform}", err=True)
        error_msg = result.error.message if result.error else "Unknown error"
        click.echo(f"  Error: {error_msg}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("platforms", nargs=-1, required=True)
@click.option("--content", "-c", required=True, help="Message content")
@click.option("--type", "msg_type", default="text", type=click.Choice(["text", "markdown"]))
@click.option("--json", "json_output", is_flag=True, help="Output result as JSON")
def send_multi(
    platforms: tuple[str, ...],
    content: str,
    msg_type: str,
    json_output: bool
) -> None:
    """Send a message to multiple platforms."""
    message = build_message(msg_type, content)

    sender = MessageSender()
    urls: dict[str, str] = {}
    result = asyncio.run(sender.send_multi(message, list(platforms), urls))

    if json_output:
        click.echo(json.dumps(result.__dict__, indent=2, ensure_ascii=False))
    else:
        click.echo(f"Total: {result.total}")
        click.echo(f"Success: {result.success_count}")
        click.echo(f"Failed: {result.failed_count}")


@cli.command()
@click.option("--content", "-c", required=True, help="Message content")
@click.option("--type", "msg_type", default="text", type=click.Choice(["text", "markdown"]))
@click.option("--json", "json_output", is_flag=True, help="Output result as JSON")
def send_auto(
    content: str,
    msg_type: str,
    json_output: bool
) -> None:
    """Send a message to all available platforms."""
    message = build_message(msg_type, content)

    sender = MessageSender()
    result = asyncio.run(sender.send_auto(message))

    if json_output:
        click.echo(json.dumps(result.__dict__, indent=2, ensure_ascii=False))
    else:
        click.echo(f"Sent to: {', '.join(result.sent_platforms)}")
        if result.skipped_platforms:
            click.echo(f"Skipped: {', '.join(result.skipped_platforms)}")


@cli.command()
@click.argument("platform")
def info(platform: str) -> None:
    """Show platform information."""
    adapter = default_registry.get(platform)

    if not adapter:
        click.echo(f"Unknown platform: {platform}", err=True)
        sys.exit(1)

    rate_limit = adapter.get_rate_limit_info()

    click.echo(f"Platform: {adapter.platform}")
    click.echo(f"Priority: {adapter.priority}")
    click.echo(f"Available: {adapter.is_available()}")
    click.echo(f"Rate Limit: {rate_limit.max_requests}/min")
    click.echo(f"Webhook URL: {adapter.get_webhook_url()}")


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
