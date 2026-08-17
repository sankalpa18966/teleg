# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY telegram_media_transfer.py .
COPY find_channel_id.py .
COPY web_app.py .
COPY templates/ ./templates/

# Create directory for downloads
RUN mkdir -p telegram_downloads

# Create volume for session files (to persist login)
VOLUME ["/app/session_data"]

# Set environment variables (these will be overridden by docker-compose or command line)
ENV API_ID=""
ENV API_HASH=""
ENV PHONE=""
ENV SOURCE_CHANNEL=""
ENV TARGET_CHANNEL=""
ENV TRANSFER_LIMIT=""
ENV DELAY="3"
ENV DELETE_AFTER_UPLOAD="True"

# Expose port 3000
EXPOSE 3000

# Run the web UI
CMD ["python", "-u", "web_app.py"]
