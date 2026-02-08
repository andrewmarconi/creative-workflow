# Contributing to Generative Creative Lab

Thank you for your interest in contributing to Generative Creative Lab! This document provides guidelines and instructions for contributing to the project.

## Welcome

Generative Creative Lab is a Django + Celery application for multi-model diffusion image generation with TV spot adaptation capabilities. We welcome contributions in many forms:

- **Code**: Bug fixes, new features, performance improvements
- **Documentation**: Improvements to guides, API docs, tutorials
- **Issues**: Bug reports, feature requests, questions
- **Testing**: Adding test coverage, testing edge cases

## Development Setup

### Prerequisites

- **Python 3.12+**: Required for the project
- **uv**: Fast Python package manager
- **Docker**: For PostgreSQL 17 and Valkey containers
- **Git**: For version control

### Initial Setup

1. **Clone the repository**:
   ```bash
   git clone git@github.com:andrewmarconi/generative-creative-lab.git
   cd generative-creative-lab
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Set up environment variables**:
   - Copy `.env.example` to `.env` (if available)
   - Configure required variables: `POSTGRES_*`, `VALKEY_*`, `DJANGO_SECRET_KEY`
   - Optional: `ANTHROPIC_API_KEY`, `CIVITAI_API_KEY`, `MODEL_BASE_PATH`

4. **Start the development environment**:
   ```bash
   ./start.sh  # Recommended: waits for containers to be ready
   # OR
   uv run honcho start  # Parallel start without dependency ordering
   ```

5. **Run database migrations**:
   ```bash
   uv run manage.py migrate
   uv run manage.py import_presets
   uv run manage.py createsuperuser
   ```

6. **Access the application**:
   - Django admin: http://localhost:8000/admin
   - Flower task monitor: http://localhost:5555
   - Grafana logs: http://localhost:3000

## Code Style

### Python Style

- Follow **PEP 8** conventions
- Use **Google-style docstrings** for functions, classes, and modules
- Keep lines under **100 characters** where practical
- Use **type hints** for function parameters and return values

### Import Ordering

Organize imports in the following order (separated by blank lines):

1. Standard library imports
2. Third-party imports
3. Django imports
4. Local application imports

Example:
```python
import os
from typing import Dict, Optional

import torch
from diffusers import DiffusionPipeline

from django.db import models

from cw.lib.config import PresetsConfig
from cw.lib.models.base import BaseModel
```

### Docstring Format

Use Google-style docstrings:

```python
def generate_image(prompt: str, steps: int = 30) -> str:
    """Generate an image from a text prompt.

    Args:
        prompt: The text description of the image to generate.
        steps: Number of diffusion steps to run. Defaults to 30.

    Returns:
        Path to the generated image file.

    Raises:
        ValueError: If prompt is empty or steps is negative.
    """
    pass
```

### Type Hints

- Use type hints for all function parameters and return values
- Use `Optional[T]` for nullable values
- Use `Dict`, `List`, `Tuple` from `typing` for complex types
- Use union types with `|` syntax (Python 3.10+) where appropriate

## Making Changes

### Fork and Branch Workflow

1. **Fork the repository** on GitHub
2. **Clone your fork** locally
3. **Create a feature branch** from `develop`:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

### Branch Naming Conventions

Use descriptive branch names with prefixes:

- `feature/` - New features (e.g., `feature/add-flux2-model`)
- `fix/` - Bug fixes (e.g., `fix/lora-loading-error`)
- `docs/` - Documentation updates (e.g., `docs/update-readme`)
- `refactor/` - Code refactoring (e.g., `refactor/simplify-pipeline`)
- `test/` - Adding or updating tests (e.g., `test/add-model-tests`)

### Commit Message Format

Write clear, descriptive commit messages:

```
Brief summary (50 chars or less)

More detailed explanation if needed. Wrap at 72 characters.
- Bullet points are okay
- Use present tense ("Add feature" not "Added feature")
- Reference issues: Fixes #123, Closes #456
```

Examples:
```
Add Flux 2.5 model support

Implement Flux 2.5 model with updated pipeline configuration
and 8-bit quantization support. Closes #42
```

### Testing Requirements

- **Write tests** for new features and bug fixes
- **Run existing tests** before submitting: `uv run python test_admin.py`
- **Test manually** in the admin interface where applicable
- **Update documentation** if behavior changes

## Pull Request Process

### Before Submitting

- [ ] Code follows project style guidelines
- [ ] All tests pass locally
- [ ] Documentation is updated (if applicable)
- [ ] Commit messages are clear and descriptive
- [ ] Branch is up to date with `develop`
- [ ] No unnecessary files included (check `.gitignore`)

### PR Title and Description

**Title**: Use the same format as commit messages (clear and descriptive)

**Description**: Include the following sections:

```markdown
## Summary
Brief description of what this PR does.

## Changes
- Bullet list of specific changes
- Keep it concise and scannable

## Related Issues
Fixes #123
Closes #456

## Testing
How to test these changes (if not obvious).

## Screenshots
(If UI changes are involved)
```

### Review Process

1. **Automated checks**: CI/CD will run tests and linting
2. **Code review**: Maintainers will review your code
3. **Feedback**: Address any requested changes
4. **Approval**: At least one maintainer approval required
5. **Merge**: Maintainer will merge once approved

### Merge Requirements

- All CI checks passing
- At least one approving review from a maintainer
- No merge conflicts with target branch
- Branch is up to date with `develop`

## Issue Guidelines

### Bug Reports

When reporting bugs, include:

- **Description**: Clear description of the problem
- **Steps to reproduce**: Numbered steps to reproduce the issue
- **Expected behavior**: What you expected to happen
- **Actual behavior**: What actually happened
- **Environment**: OS, Python version, relevant package versions
- **Error messages**: Full error messages and stack traces
- **Screenshots**: If applicable

### Feature Requests

When requesting features, include:

- **Description**: Clear description of the feature
- **Use case**: Why this feature would be useful
- **Proposed solution**: How you think it should work
- **Alternatives**: Other solutions you've considered
- **Additional context**: Any other relevant information

### Documentation Issues

For documentation improvements:

- **Location**: Which file or section needs improvement
- **Issue**: What's wrong or missing
- **Suggestion**: How to improve it (if you have ideas)

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Provide constructive feedback
- Focus on what's best for the community
- Show empathy towards others

### Unacceptable Behavior

- Harassment, discrimination, or inappropriate comments
- Trolling, insulting comments, or personal attacks
- Publishing others' private information
- Other conduct that could reasonably be considered inappropriate

### Enforcement

Project maintainers are responsible for clarifying standards and will take appropriate action in response to unacceptable behavior.

## Getting Help

### Where to Ask Questions

- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For questions and general discussion (if enabled)
- **Pull Request Comments**: For questions about specific code changes

### Response Time Expectations

This is an open-source project maintained by volunteers. We'll do our best to respond within:

- **Critical bugs**: 1-2 days
- **General issues**: 3-7 days
- **Feature requests**: When we have capacity
- **Pull requests**: 3-7 days for initial review

## Additional Resources

- [README.md](README.md) - Project overview and quick start
- [CLAUDE.md](CLAUDE.md) - Detailed development guide
- [CHANGELOG.md](CHANGELOG.md) - Version history and changes
- [Documentation](docs/) - Sphinx documentation

## License

By contributing to Generative Creative Lab, you agree that your contributions will be licensed under the same license as the project.

---

Thank you for contributing to Generative Creative Lab!
