#!/bin/sh
set -e

echo "==> Running database migrations..."
alembic upgrade head

echo "==> Starting bot..."
exec python -m app.main
