#!/bin/bash

# CLISApp Backend Quick Start Script
# Launch all backend services with one command

cd "$(dirname "$0")"

echo "🌏 CLISApp Backend Quick Start..."
echo ""

# Check Python environment
if [ -d "venv" ]; then
    echo "✅ Found virtual environment, activating..."
    source venv/bin/activate
else
    echo "⚠️  Virtual environment not found, using system Python"
fi

# Start all services
python start_all_services.py

