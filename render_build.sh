#!/usr/bin/env bash
set -o errexit

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements_api.txt

# Create necessary directories
mkdir -p data/models

echo "Build completed!"
