# Pipeline

Data dashboard web application built with FastAPI.

## Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e ".[dev]"
```

## Development

```bash
# Run the server locally
uvicorn app.main:app --reload

# Run tests
pytest

# Run linting
ruff check .
```

## API

- `GET /hello` - Returns a greeting message
