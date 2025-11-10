#!/bin/bash
# Start Analytics Dashboard for ShoesBot

echo "🚀 Starting ShoesBot Analytics Dashboard..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.8+"
    exit 1
fi

# Check if Flask is installed
if ! python3 -c "import flask" 2>/dev/null; then
    echo "📦 Installing Flask..."
    pip3 install flask
fi

# Set default port if not specified
export DASHBOARD_PORT="${DASHBOARD_PORT:-8080}"
export DASHBOARD_HOST="${DASHBOARD_HOST:-0.0.0.0}"

echo "📊 Dashboard will be available at http://localhost:${DASHBOARD_PORT}"
echo "Press Ctrl+C to stop"
echo ""

# Run the dashboard
python3 analytics_dashboard.py
