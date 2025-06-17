#!/bin/bash
set -e

# Activer le venv
source venv/bin/activate

echo "🚀 Launching application..."
python3 main.py --logs
