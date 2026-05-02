FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ANSIBLE_HOST_KEY_CHECKING=False

RUN apt-get update \
    && apt-get install -y --no-install-recommends git openssh-client sshpass curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir ansible pywinrm requests pyyaml pytest

WORKDIR /workspace
