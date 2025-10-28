# Multi-stage build for smaller final image
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN useradd -m -u 1001 mcpuser && \
    mkdir -p /app/data /app/logs && \
    chown -R mcpuser:mcpuser /app

# Copy Python dependencies from builder
COPY --from=builder --chown=mcpuser:mcpuser /root/.local /home/mcpuser/.local

# Copy application code
COPY --chown=mcpuser:mcpuser src/ ./src/
COPY --chown=mcpuser:mcpuser config/ ./config/

# Set environment variables
ENV PATH=/home/mcpuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATABASE_PATH=/app/data/database.db \
    SERVER_HOST=0.0.0.0 \
    SERVER_PORT=8080

# Switch to non-root user
USER mcpuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Run the application
CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8080"]
