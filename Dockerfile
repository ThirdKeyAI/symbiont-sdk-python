# Multi-stage build for smaller final image
FROM python:3.11-slim AS builder

# Set build environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create and use non-root user
RUN groupadd --gid 1001 symbiont && \
    useradd --uid 1001 --gid symbiont --shell /bin/bash --create-home symbiont

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt requirements-dev.txt ./
RUN pip install --user --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Install the package
RUN pip install --user .

# Production stage
FROM python:3.11-slim

# Set runtime environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/symbiont/.local/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1001 symbiont && \
    useradd --uid 1001 --gid symbiont --shell /bin/bash --create-home symbiont

# Copy installed packages from builder
COPY --from=builder --chown=symbiont:symbiont /root/.local /home/symbiont/.local

# Copy source code
WORKDIR /app
COPY --chown=symbiont:symbiont . .

# Switch to non-root user
USER symbiont

# Verify installation
RUN python -c "import symbiont; print(f'Symbiont SDK v{symbiont.__version__} installed successfully')"

# Default command - Python REPL with SDK available
CMD ["python", "-c", "import symbiont; print('Symbiont SDK ready. Use: from symbiont import SymbiontClient'); exec(open('/dev/stdin').read()) if not __import__('sys').stdin.isatty() else __import__('code').interact(local=globals())"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import symbiont; print('OK')" || exit 1

# Labels for metadata
LABEL org.opencontainers.image.title="Symbiont Python SDK" \
      org.opencontainers.image.description="Python SDK for Symbiont platform with Tool Review and Runtime APIs" \
      org.opencontainers.image.url="https://github.com/thirdkeyai/symbiont-sdk-python" \
      org.opencontainers.image.source="https://github.com/thirdkeyai/symbiont-sdk-python" \
      org.opencontainers.image.vendor="ThirdKey.ai" \
      org.opencontainers.image.licenses="MIT"