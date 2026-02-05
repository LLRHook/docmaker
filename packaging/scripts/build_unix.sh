#!/bin/bash
# macOS/Linux build script for Docmaker desktop application
# Run from the repository root: ./packaging/scripts/build_unix.sh

set -e

# Get the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "Building Docmaker for $(uname -s)"
echo "=============================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 not found in PATH"
    exit 1
fi

# Run the build script
python3 packaging/scripts/build.py "$@"
