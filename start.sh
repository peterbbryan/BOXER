#!/bin/bash

# VibeCortex Data Labeling Tool Startup Script

echo "🚀 Starting VibeCortex Data Labeling Tool..."

# Activate virtual environment
source venv/bin/activate

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ Virtual environment activated: $VIRTUAL_ENV"
else
    echo "❌ Failed to activate virtual environment"
    exit 1
fi

# Install dependencies if needed
echo "📦 Checking dependencies..."
pip install -r requirements.txt --quiet

# Start the application
echo "🌐 Starting FastAPI server..."
python run.py
