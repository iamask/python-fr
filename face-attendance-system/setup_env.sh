#!/bin/bash
# setup_env.sh - Environment setup script for macOS
# Run this first: chmod +x setup_env.sh && ./setup_env.sh

set -e

echo "=============================================="
echo "  Face Recognition Attendance System Setup"
echo "=============================================="

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "⚠️  Warning: This script is optimized for macOS"
    echo "   You may need to install cmake and libomp manually"
fi

echo ""
echo "📦 Step 1: Checking system dependencies..."

# Check for Homebrew
if ! command -v brew &> /dev/null; then
    echo "❌ Homebrew not found. Please install Homebrew first:"
    echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    exit 1
fi

# Install system dependencies
echo "   Installing cmake..."
brew install cmake 2>/dev/null || echo "   cmake already installed"

echo "   Installing libomp (required for Apple Silicon)..."
brew install libomp 2>/dev/null || echo "   libomp already installed"

echo ""
echo "🐍 Step 2: Setting up Python virtual environment..."

# Create virtual environment
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "   ✅ Virtual environment created"
else
    echo "   ℹ️  Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate

echo ""
echo "📥 Step 3: Installing Python packages..."
echo "   (This may take 5-10 minutes due to dlib compilation)"

# Upgrade pip
pip install --upgrade pip -q

# Install packages in order (important for macOS)
echo "   Installing numpy..."
pip install numpy -q

echo "   Installing cmake (Python package)..."
pip install cmake -q

echo "   Installing dlib (this takes a while)..."
pip install dlib 2>&1 | grep -E "(Successfully|error|ERROR)" || echo "      Still compiling..."

echo "   Installing face-recognition..."
pip install face-recognition -q

echo "   Installing opencv-python..."
pip install opencv-python -q

echo "   Installing customtkinter..."
pip install customtkinter -q

echo "   Installing Pillow..."
pip install Pillow -q

echo ""
echo "🗂️  Step 4: Creating project directories..."

mkdir -p images data

# Create empty attendance.csv with headers if it doesn't exist
if [ ! -f "data/attendance.csv" ]; then
    echo "Name,Date,Time,Status" > data/attendance.csv
    echo "   ✅ Created data/attendance.csv"
fi

echo ""
echo "=============================================="
echo "  ✅ Setup Complete!"
echo "=============================================="
echo ""
echo "To run the application:"
echo "   source venv/bin/activate"
echo "   python main.py"
echo ""
echo "Or use the activation script:"
echo "   source venv/bin/activate && python main.py"
echo ""
