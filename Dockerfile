FROM python:3.12-slim

# Install dependencies needed to build nsjail
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    libprotobuf-dev \
    protobuf-compiler \
    libnl-route-3-dev \
    libcap-dev \
    pkg-config \
    ca-certificates \
    flex \
    bison \
 && rm -rf /var/lib/apt/lists/*

# Build & install nsjail
RUN git clone https://github.com/google/nsjail.git /opt/nsjail \
 && cd /opt/nsjail \
 && make \
 && cp nsjail /usr/local/bin/nsjail \
 && rm -rf /opt/nsjail

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all app code & nsjail config
COPY . ./

# Expose port for Cloud Run / local usage
EXPOSE 8080

# Use gunicorn in container; bind to $PORT (Cloud Run) or 8080 locally
CMD ["sh", "-c", "gunicorn -b 0.0.0.0:${PORT:-8080} app:app"]
