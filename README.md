# QueryMind AI - Backend

QueryMind AI is an advanced Text-to-SQL backend engine designed to translate natural language queries into SQL, perform validations, run execution, and format the resulting datasets.

## Project Setup

### Prerequisites
Make sure you have [uv](https://github.com/astral-sh/uv) installed.

### Setup Instructions
1. Clone the repository and navigate to the backend directory:
   ```bash
   cd querymind-ai/backend
   ```

2. Initialize virtual environment and install packages:
   ```bash
   # Create virtual environment
   uv venv

   # Install dependencies
   uv sync
   ```

3. Setup environment variables:
   ```bash
   cp .env.example .env
   ```

## Running Tests
Run the suite of unit tests with:
```bash
uv run pytest
```

## Running the Server
*(Placeholder for running the API server)*
```bash
# To run the development server (available in Component 1.x)
# uv run uvicorn querymindai_backend.main:app --reload
```
