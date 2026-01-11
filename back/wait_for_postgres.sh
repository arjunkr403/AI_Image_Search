#!/bin/sh
set -e

echo "Waiting for Postgres..."

until pg_isready -h postgres -p 5432 -U admin; do
  sleep 2
done

echo "Postgres is ready!"
exec "$@"
