FROM python:3.12-slim

# Install deps for nsjail
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    libprotobuf-dev \
    protobuf-compiler \
    libnl-route-3-200 \
    libnl-route-3-dev \
    libcap-dev \
    pkg-config \
    ca-certificates \
    flex \
    bison \
 && rm -rf /var/lib/apt/lists/*

# ---- Build nsjail ----
RUN git clone https://github.com/google/nsjail.git /opt/nsjail && \
    cd /opt/nsjail && make && cp nsjail /usr/local/bin/nsjail && \
    rm -rf /opt/nsjail

WORKDIR /app
RUN mkdir -p /runtime

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py /app/
COPY nsjail.cfg /app/
COPY runtime/ /runtime/

# Cloud Run + nsjail: run as non-root
RUN useradd -m -u 1001 appuser
USER appuser

EXPOSE 8080

CMD ["sh", "-c", "gunicorn -b 0.0.0.0:${PORT:-8080} app:app"]
