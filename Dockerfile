# Builder
FROM python:3.13-alpine AS builder

WORKDIR /app

RUN apk add --no-cache \
        bash \
        python3-dev \
        py3-pip \
        py3-virtualenv \
        build-base \
        libffi-dev \
        openssl-dev

COPY requirements.txt .

RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

COPY . .

# Runtime
FROM python:3.13-alpine

WORKDIR /app

COPY --from=builder /install /usr/local
COPY --from=builder /app /app

USER 1000

CMD ["python3", "main.py"]
