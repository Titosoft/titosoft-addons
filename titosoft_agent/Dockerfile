# Dual-purpose:
# - Add-on do Home Assistant: o builder injeta BUILD_FROM (base alpine c/ python3+bashio)
# - Container standalone (servidor/CI): docker build --build-arg BUILD_FROM=python:3.12-slim
ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.12-alpine3.20
FROM ${BUILD_FROM}

WORKDIR /agent

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt || \
    pip3 install --no-cache-dir -r requirements.txt

COPY titosoft_agent ./titosoft_agent
COPY run.sh /run.sh
RUN chmod +x /run.sh

CMD ["/run.sh"]
