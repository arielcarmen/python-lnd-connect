#!/bin/bash

# LND Lightning API Run Script
echo "🚀 Starting LND Lightning API Server..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup.sh first."
    exit 1
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please copy and configure it:"
    echo "   cp .env.example .env"
    echo "   # Then edit .env with your LND configuration"
    exit 1
fi

# Check if gRPC stubs exist
if [ ! -f "lightning_pb2.py" ] || [ ! -f "lightning_pb2_grpc.py" ]; then
    echo "❌ gRPC stubs not found. Please run setup.sh first."
    exit 1
fi

# Start the server
echo "🌟 Starting API server..."
echo "📚 API docs will be available at: http://localhost:8000/docs"
echo "🔍 Health check: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 main.py