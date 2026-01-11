# Nexobot Article Scraper
# Build: docker build -t nexobot .
# Run:   docker run -v ./config.json:/app/config.json -v ./output:/app/output nexobot --config config.json

FROM python:3.11-slim

# Prevent Python from buffering stdout/stderr (fixes missing docker logs)
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY nexobot/ ./nexobot/
COPY run.py .

# Create output directory
RUN mkdir -p output

# Default command
ENTRYPOINT ["python", "run.py"]
CMD ["--help"]
