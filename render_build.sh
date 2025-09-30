#!/usr/bin/env bash
# exit on error
set -o errexit

# Install Python dependencies
pip install -r requirements_api.txt

# Download spaCy language model (if using)
# python -m spacy download en_core_web_sm

# Create directories
mkdir -p data/models

# Any other build commands
echo "Build completed!"
