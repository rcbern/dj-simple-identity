# Dockerfile
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set work directory
WORKDIR /app

# Copy dependency files first to leverage Docker cache
COPY pyproject.toml uv.lock ./

# Sync dependencies
# We use --system so we don't need to activate a venv, but you can omit it to use .venv
RUN uv sync --frozen --no-dev

# Copy the rest of the application code
COPY . .

# Run the application (this gets overridden by docker-compose for dev)
CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]