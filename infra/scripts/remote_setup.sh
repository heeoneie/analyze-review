#!/usr/bin/env bash
set -euo pipefail

APP_USER=${APP_USER:-ec2-user}
APP_ROOT=/opt/analyze-review
WEB_ROOT=/var/www/analyze-review
ENV_DIR=/etc/analyze-review

sudo yum update -y
sudo yum install -y nginx python3 python3-pip
sudo systemctl enable --now nginx

sudo mkdir -p "$APP_ROOT/current" "$WEB_ROOT" "$ENV_DIR"
sudo chown -R "$APP_USER":"$APP_USER" "$APP_ROOT" "$WEB_ROOT"

if [ ! -f "$ENV_DIR/backend.env" ]; then
  echo "backend.env not found. Create $ENV_DIR/backend.env with OPENAI_API_KEY and ALLOWED_ORIGINS."
fi
