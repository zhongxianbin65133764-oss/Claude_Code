FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install Python deps first so the layer is cached when only code changes.
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Then copy the application.
COPY polymarket_arb ./polymarket_arb
COPY scripts ./scripts
COPY README.md ./

# Create a writable data dir for positions.db (mounted as a volume).
RUN mkdir -p /data && chmod 777 /data
ENV DB_PATH=/data/positions.db \
    LOG_PATH=/data/arb_bot.log

# The default command runs the bot. The dashboard image override the
# CMD via docker-compose.
CMD ["python", "-m", "polymarket_arb.main"]
