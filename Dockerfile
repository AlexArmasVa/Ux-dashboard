# Base image
FROM python:3.10-slim

# Environment
ENV PYTHONUNBUFFERED=1
ENV CHROME_BIN=/usr/bin/chromium

# Install system packages & Chromium
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libffi-dev \
    libcairo2 \
    libpango-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libjpeg-dev \
    libxml2 \
    libxslt1.1 \
    shared-mime-info \
    wget \
    unzip \
    chromium \
    chromium-driver \
    fonts-liberation \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install Lighthouse CLI globally
RUN npm install -g lighthouse

# Set working directory
WORKDIR /app

# Copy source code
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir \
    streamlit pandas weasyprint matplotlib playwright

# Install Playwright dependencies + browsers
RUN playwright install --with-deps

# Expose port
EXPOSE 8501

# Start Streamlit app
CMD ["streamlit", "run", "dashboard.py", "--server.port=8501", "--server.enableCORS=false"]