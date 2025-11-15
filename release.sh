#!/bin/bash
# Script de release para Railway
# Executa migrações antes de iniciar o servidor

set -e

echo "Running migrations..."
python manage.py migrate --noinput

echo "Migrations completed!"

