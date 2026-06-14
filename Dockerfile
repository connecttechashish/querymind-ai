# Use Python slim base image
FROM python:3.12-slim

# Install uv from the official prebuilt image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory in the container
WORKDIR /app

# Copy dependency definition files and application source code
COPY pyproject.toml uv.lock ./
COPY src ./src

# Install production dependencies (frozen dependencies, excluding dev-packages)
RUN uv sync --frozen --no-dev

# Expose the application port
EXPOSE 8000

# Set environment path to locate virtual environment binaries
ENV PATH="/app/.venv/bin:$PATH"

# Start the application using Uvicorn
CMD ["uvicorn", "querymindai_backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
