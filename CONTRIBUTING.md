# Contributing to Railyard

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

```bash
git clone https://github.com/nousresearch/railyard.git
cd railyard
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest
pytest --cov=railyard --cov-report=term-missing
```

## Code Style

- Type hints on all public APIs
- Docstrings (Google style) on classes and public methods
- Keep dependencies minimal

## Submitting Changes

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-change`)
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Architecture

- `machine.py` — DSL for defining state machines
- `runtime.py` — execution engine with tool filtering
- `log.py` — JSONL transition logging
- `replay.py` — log replay and verification
- `adapters/` — framework integrations

## Reporting Issues

Open an issue on GitHub with:
- A clear description
- Minimal reproduction steps
- Expected vs actual behavior
