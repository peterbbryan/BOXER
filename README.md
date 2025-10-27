# VibeCortex

A Python project built with Python 3.9.

## Setup

1. Create and activate a virtual environment:
   ```bash
   python3.9 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install the package in development mode:
   ```bash
   pip install -e .
   ```

## Development

- Run tests: `pytest`
- Format code: `black src/ tests/`
- Lint code: `flake8 src/ tests/`
- Type checking: `mypy src/`

## Project Structure

```
VibeCortex/
├── src/                    # Source code
├── tests/                  # Test files
├── docs/                   # Documentation
├── venv/                   # Virtual environment
├── requirements.txt        # Dependencies
├── setup.py               # Package setup
└── README.md              # This file
```
