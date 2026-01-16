#!/bin/bash

# Test script for running the example app locally

echo "Testing Vesla Example App locally..."
echo "===================================="
echo

# Check if in virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
fi

echo "Installing dependencies..."
pip install -q -r requirements.txt

echo "Starting Flask app on http://localhost:5000"
echo "Press Ctrl+C to stop"
echo
python app.py
