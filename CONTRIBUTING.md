# Contributing to PiSecure

Thank you for your interest in contributing to PiSecure! We welcome contributions from the Raspberry Pi community and beyond. This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)
- [Community](#community)

## Code of Conduct

This project follows a code of conduct to ensure a welcoming environment for all contributors. By participating, you agree to:

- Be respectful and inclusive
- Focus on constructive feedback
- Accept responsibility for mistakes
- Show empathy towards other contributors
- Help create a positive community

## Getting Started

### Prerequisites

- Python 3.7 or higher
- Git
- Raspberry Pi (for hardware testing) or Docker (for development)

### Quick Setup

```bash
# Fork and clone the repository
git clone https://github.com/yourusername/PiSecure.git
cd PiSecure

# Set up development environment
make dev-setup

# Run basic tests
make test
```

## Development Setup

### Using Make (Recommended)

```bash
# Install in development mode with all dependencies
make install-dev

# Run full test suite
make dev-test

# Build documentation
make docs
```

### Manual Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install with development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Docker Development

```bash
# Build development container
make docker-build

# Run tests in container
make docker-test

# Run interactive shell in container
docker run --rm -it -v $(pwd):/app pisecure bash
```

## Development Workflow

### 1. Choose an Issue

- Check [GitHub Issues](https://github.com/UnderhillForge/PiSecure/issues) for open tasks
- Look for issues labeled `good first issue` or `help wanted`
- Comment on the issue to indicate you're working on it

### 2. Create a Branch

```bash
# Create a feature branch
git checkout -b feature/amazing-feature

# Or fix a bug
git checkout -b fix/issue-number-description
```

### 3. Implement Changes

- Write clean, well-documented code
- Add tests for new functionality
- Update documentation as needed
- Follow the code standards below

### 4. Test Your Changes

```bash
# Run tests
make test

# Run with coverage
make test-cov

# Run linting
make lint

# Test formatting
make format-check
```

### 5. Submit a Pull Request

- Push your branch to GitHub
- Create a pull request with a clear description
- Reference any related issues
- Wait for review and address feedback

## Code Standards

### Python Style

We follow [PEP 8](https://pep8.org/) with some modifications:

```python
# Good: Descriptive variable names
device_fingerprint = generate_device_fingerprint()

# Bad: Unclear abbreviations
df = gen_dfp()

# Good: Type hints for function parameters
def authenticate_device(self, cert_pem: str, timeout: int = 30) -> bool:
    pass

# Good: Docstrings for all public functions
def verify_signature(self, data: bytes, signature: bytes, public_key) -> bool:
    """
    Verify a cryptographic signature.

    Args:
        data: The data that was signed
        signature: The signature to verify
        public_key: The public key to use for verification

    Returns:
        True if signature is valid, False otherwise

    Raises:
        ValueError: If parameters are invalid
    """
    pass
```

### Code Formatting

We use automated formatting tools:

- **[Black](https://black.readthedocs.io/)** for code formatting (line length: 100)
- **[isort](https://isort.readthedocs.io/)** for import sorting
- **[flake8](https://flake8.pycqa.org/)** for linting
- **[mypy](https://mypy.readthedocs.io/)** for type checking

```bash
# Format code
make format

# Check formatting without changes
make format-check

# Run all quality checks
make lint
```

### Naming Conventions

```python
# Classes: PascalCase
class DeviceFingerprint:
    pass

# Functions and methods: snake_case
def generate_fingerprint(self):
    pass

# Constants: UPPER_CASE
MAX_RETRY_ATTEMPTS = 3
DEFAULT_TIMEOUT = 30

# Private methods: _leading_underscore
def _validate_input(self, data):
    pass

# Module-level variables: _leading_underscore
_default_config = {}
```

### Error Handling

```python
# Good: Specific exceptions with context
def load_certificate(self, cert_path: str):
    try:
        with open(cert_path, 'rb') as f:
            cert_data = f.read()
        return x509.load_pem_x509_certificate(cert_data)
    except FileNotFoundError:
        raise CertificateError(f"Certificate file not found: {cert_path}")
    except ValueError as e:
        raise CertificateError(f"Invalid certificate format: {e}")

# Bad: Generic exceptions
def load_certificate(self, cert_path: str):
    try:
        with open(cert_path) as f:
            return f.read()
    except:
        raise Exception("Certificate error")
```

## Testing

### Test Structure

```
tests/
├── unit/                    # Unit tests
│   ├── test_blockchain.py
│   └── test_identity.py
├── integration/            # Integration tests
│   ├── test_full_flow.py
│   └── test_hardware.py
├── fixtures/               # Test data
└── conftest.py            # Test configuration
```

### Writing Tests

```python
import pytest
from pisecure.core.blockchain import SignChain

class TestSignChain:
    def test_add_transaction(self):
        """Test adding a transaction to the blockchain."""
        chain = SignChain()

        tx = {
            'type': 'test',
            'data': {'message': 'test transaction'},
            'timestamp': 1234567890
        }

        tx_hash = chain.add_transaction(tx)

        assert tx_hash
        assert len(chain.pending_transactions) == 1
        assert chain.pending_transactions[0]['hash'] == tx_hash

    def test_mine_block(self):
        """Test mining a block with pending transactions."""
        chain = SignChain()

        # Add a transaction
        tx = {'type': 'test', 'data': {}, 'timestamp': 1234567890}
        chain.add_transaction(tx)

        # Mine the block
        mined_block = chain.mine_pending_transactions()

        assert mined_block is not None
        assert len(mined_block.transactions) == 1
        assert len(chain.pending_transactions) == 0
        assert len(chain.chain) > 1  # Genesis + mined block

    @pytest.mark.parametrize("difficulty", [1, 2, 4])
    def test_proof_of_work(self, difficulty):
        """Test proof-of-work with different difficulties."""
        chain = SignChain(difficulty=difficulty)

        nonce = chain._proof_of_work("test_data", difficulty)

        # Verify the proof
        hash_result = chain._calculate_hash("test_data", nonce)
        assert hash_result.startswith('0' * difficulty)
```

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
pytest tests/unit/test_blockchain.py

# Run tests matching pattern
pytest -k "test_mine"

# Run tests in verbose mode
pytest -v

# Run tests with mock hardware
PISECURE_MOCK_HARDWARE=1 make test
```

### Test Coverage

We aim for >85% code coverage. Check coverage reports:

```bash
# Generate HTML coverage report
make test-cov

# Open in browser
open htmlcov/index.html
```

## Documentation

### Documentation Standards

- Use [Google-style docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
- Document all public APIs
- Include type hints for function parameters and return values
- Add examples for complex functionality

### Building Documentation

```bash
# Build HTML documentation
make docs

# Serve documentation locally
make serve-docs

# Auto-rebuild on changes
make docs-auto
```

### Documentation Structure

```
docs/
├── index.rst              # Main documentation page
├── getting-started.md     # Quick start guide
├── api/                   # API documentation
│   ├── core.rst
│   ├── identity.rst
│   └── updates.rst
├── examples/             # Usage examples
├── roadmap.md            # Development roadmap
└── contributing.md       # This file
```

## Submitting Changes

### Pull Request Process

1. **Fork** the repository on GitHub
2. **Clone** your fork locally
3. **Create** a feature branch
4. **Make** your changes
5. **Test** thoroughly
6. **Commit** with clear messages
7. **Push** to your fork
8. **Create** a pull request

### Commit Messages

Follow conventional commit format:

```bash
# Good commit messages
feat: add device fingerprint verification
fix: resolve certificate validation bug
docs: update installation guide
refactor: simplify blockchain consensus logic

# Bad commit messages
fixed bug
updated code
changes
```

### Pull Request Template

When creating a PR, include:

- **Description**: What changes were made and why
- **Related Issues**: Link to any related GitHub issues
- **Testing**: How the changes were tested
- **Breaking Changes**: Any breaking changes
- **Screenshots**: UI changes or demonstrations

### Code Review Process

- All PRs require review from at least one maintainer
- Address review feedback promptly
- Keep PRs focused on a single feature or fix
- Squash commits when appropriate

## Community

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General discussion and Q&A
- **Discord/Slack**: Real-time community chat (coming soon)

### Getting Help

- Check existing documentation first
- Search GitHub issues for similar problems
- Ask questions in GitHub Discussions
- Join community calls (announced in Discussions)

### Recognition

Contributors are recognized in several ways:

- **GitHub Contributors**: Listed in repository insights
- **CHANGELOG**: Mentioned in release notes
- **Credits**: Special thanks in documentation
- **Community**: Featured in community spotlights

### Governance

PiSecure is maintained by the core team with input from the community:

- **Maintainers**: Oversee code quality and releases
- **Contributors**: Community members who contribute code
- **Community**: All users providing feedback and testing

---

## Development Checklist

Before submitting your contribution:

- [ ] Code follows style guidelines
- [ ] All tests pass (`make test`)
- [ ] Code is linted (`make lint`)
- [ ] Documentation updated
- [ ] Type hints added
- [ ] Commit messages are clear
- [ ] PR description is detailed
- [ ] Related issues are linked

Thank you for contributing to PiSecure! 🚀🔒⚡