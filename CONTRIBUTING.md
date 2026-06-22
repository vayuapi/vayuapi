# Contributing to VayuAPI

Thank you for your interest in contributing to VayuAPI! This document provides guidelines and instructions for contributing.

## Code of Conduct

We are committed to providing a welcoming and inclusive environment. Please be respectful and considerate in all interactions.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/vayuapi/vayuapi/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (Python version, OS, etc.)
   - Code samples if applicable

### Suggesting Features

1. Check existing issues and discussions
2. Create a new issue with:
   - Clear description of the feature
   - Use cases and benefits
   - Potential implementation approach

### Contributing Code

#### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/vayuapi/vayuapi.git
cd vayuapi

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

#### Development Workflow

1. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clean, documented code
   - Follow the coding style (PEP 8)
   - Add type hints
   - Write tests

3. **Run tests**
   ```bash
   pytest
   pytest --cov=vayuapi  # With coverage
   ```

4. **Run linters**
   ```bash
   black .
   ruff check .
   mypy vayuapi
   ```

5. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add amazing feature"
   ```

   Follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation changes
   - `test:` - Test changes
   - `refactor:` - Code refactoring
   - `perf:` - Performance improvements

6. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a Pull Request on GitHub

## Coding Standards

### Style Guide

- Follow PEP 8
- Use type hints for all functions
- Maximum line length: 100 characters
- Use docstrings for classes and functions

### Docstring Format

```python
def my_function(param1: str, param2: int) -> bool:
    """
    Brief description of function.
    
    More detailed description if needed.
    
    Args:
        param1: Description of param1
        param2: Description of param2
    
    Returns:
        Description of return value
    
    Raises:
        ValueError: When something goes wrong
    
    Example:
        ```python
        result = my_function("hello", 42)
        ```
    """
    pass
```

### Testing

- Write tests for all new features
- Maintain or improve code coverage
- Use pytest fixtures for common setup
- Test async code with `pytest-asyncio`

Example test:

```python
import pytest
from vayuapi import VayuAPI

@pytest.fixture
def app():
    return VayuAPI()

@pytest.mark.asyncio
async def test_home_endpoint(app):
    @app.get("/")
    async def home():
        return {"message": "Hello"}
    
    # Test implementation...
```

## Project Structure

```
vayuapi/
├── vayuapi/
│   ├── core/           # Core framework
│   ├── orm/            # ORM integrations
│   ├── admin/          # Admin panel
│   ├── security/       # Security features
│   ├── scheduler/      # Task scheduling
│   ├── ai/             # AI integrations
│   └── utils/          # Utilities
├── examples/           # Example applications
├── tests/              # Test suite
├── docs/               # Documentation
└── README.md
```

## Areas for Contribution

### High Priority

- [ ] Documentation improvements
- [ ] Test coverage improvements
- [ ] Performance optimizations
- [ ] Bug fixes

### Feature Requests

- [ ] GraphQL support
- [ ] Additional ORM integrations
- [ ] More middleware options
- [ ] Enhanced admin panel features
- [ ] Additional AI/ML integrations

### Good First Issues

Look for issues labeled `good first issue` in the issue tracker. These are typically:
- Documentation improvements
- Simple bug fixes
- Adding examples
- Writing tests

## Documentation

When adding features:
1. Update relevant documentation
2. Add docstrings to all public APIs
3. Update README.md if needed
4. Add examples when appropriate

## Release Process

(For maintainers)

1. Update version in `pyproject.toml` and `vayuapi/__init__.py`
2. Update CHANGELOG.md
3. Create release tag
4. Publish to PyPI

## Questions?

- 💬 [Discord](https://discord.gg/vayuapi)
- 📧 Email: dev@vayuapi.dev
- 🐛 [GitHub Issues](https://github.com/vayuapi/vayuapi/issues)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to VayuAPI! 🔥
