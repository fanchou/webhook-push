# Contributing to Webhook Push Skill

Thank you for your interest in contributing to the webhook-push skill! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on what is best for the community

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Poetry (for dependency management)
- Git

### Setup Development Environment

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/webhook-push.git
   cd webhook-push
   ```

3. Install dependencies using Poetry:
   ```bash
   poetry install
   ```

4. Activate the virtual environment:
   ```bash
   poetry shell
   ```

## Development Workflow

### Making Changes

1. Create a new branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following the coding standards below

3. Test your changes:
   ```bash
   # Run tests
   pytest

   # Run with coverage
   pytest --cov=webhook_push --cov-report=html

   # Run type checking
   mypy src/webhook_push

   # Run linting
   ruff check src/webhook_push
   black --check src/webhook_push
   isort --check-only src/webhook_push
   ```

4. Commit your changes:
   ```bash
   git add .
   git commit -m "Brief description of changes"
   ```

### Commit Message Guidelines

Use clear and descriptive commit messages:

- `feat: add support for new message type`
- `fix: resolve rate limit handling bug`
- `docs: update API documentation`
- `test: add integration tests for sender`
- `refactor: simplify converter logic`

### Pull Request Process

1. Push your changes to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

2. Open a pull request against the main branch

3. Ensure your PR:
   - Has a clear title and description
   - References any related issues
   - Passes all CI checks
   - Includes tests for new features
   - Updates documentation as needed

4. Wait for code review and address feedback

## Coding Standards

### Python Style Guide

- Follow PEP 8 guidelines
- Use `black` for code formatting (line length: 100)
- Use `isort` for import sorting
- Use `ruff` for linting
- Use `mypy` for type checking

### Code Organization

```
src/webhook_push/
├── models/          # Data models and schemas
├── adapters/        # Platform adapters
├── converters/      # Message converters
├── sender/          # Message sender
└── cli.py          # Command-line interface
```

### Type Hints

All functions should include type hints:

```python
from typing import Optional

def send_message(
    message: UnifiedMessage,
    platform: str,
    webhook_url: str,
    timeout: Optional[int] = None
) -> SendResult:
    """Send a message to the specified platform."""
    ...
```

### Documentation

All public modules, classes, and functions should have docstrings:

```python
def convert_to_markdown(text: str) -> str:
    """Convert plain text to markdown format.

    Args:
        text: Plain text to convert

    Returns:
        Formatted markdown string
    """
    ...
```

## Testing

### Writing Tests

- Place tests in the `tests/` directory
- Use descriptive test names
- Follow the Arrange-Act-Assert pattern
- Mock external API calls

```python
def test_send_text_message_success():
    """Test successful text message sending."""
    # Arrange
    message = UnifiedMessage(content={"type": "text", "body": {"text": "Hello"}})
    sender = MessageSender()

    # Act
    result = await sender.send(message, "dingtalk", webhook_url=TEST_URL)

    # Assert
    assert result.success is True
    assert result.message_id is not None
```

### Test Coverage

- Aim for >80% code coverage
- Add tests for bug fixes
- Include edge cases and error conditions

## Adding Features

### New Message Type

1. Add body model in `models/__init__.py`
2. Add converter in `converters/__init__.py`
3. Update platform adapters in `adapters/__init__.py`
4. Add tests in `tests/test_converters.py`
5. Update SKILL.md with usage examples

### New Platform

1. Create platform adapter in `adapters/__init__.py`
2. Add platform-specific converters
3. Add configuration options
4. Write comprehensive tests
5. Document platform-specific notes

## Documentation

### Updating SKILL.md

When adding features:
- Update the "Core Capabilities" section
- Add usage examples
- Document any new configuration options
- Update the "Message Types" section

### Updating README.md

Keep the README focused on:
- Quick start guide
- Basic installation
- Simple usage examples
- Links to detailed documentation

## Questions or Issues?

- Open an issue on GitHub for bugs or feature requests
- Check existing issues first
- Provide detailed information when reporting bugs
- Include steps to reproduce

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
