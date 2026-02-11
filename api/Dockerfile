# --------------------------------------------------
# Stage 1: Build dependencies
# --------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/build/deps -r requirements.txt

# --------------------------------------------------
# Stage 2: Production image
# --------------------------------------------------
FROM python:3.11-slim

# Security: run as non-root
RUN useradd --create-home appuser
WORKDIR /home/appuser

# Copy dependencies from builder
COPY --from=builder /build/deps /usr/local/lib/python3.11/site-packages/

# Copy application code
COPY app/ ./app/

# Set environment
ENV PYTHONUNBUFFERED=1

USER appuser

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
