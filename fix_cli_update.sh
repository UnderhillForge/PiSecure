#!/bin/bash
"""
PiSecure CLI Update Fix Script
==============================

This script fixes git conflicts and updates PiSecure with latest CLI fixes.
Run this on your Raspberry Pi to resolve import and syntax errors.
"""

set -e

echo "🔧 PiSecure CLI Update Fix"
echo "=========================="

# Check if we're in the right directory
if [[ ! -d "pisecure" ]]; then
    echo "❌ Error: Run this script from the PiSecure directory"
    echo "   cd /home/pi/PiSecure"
    exit 1
fi

echo "📁 Working directory: $(pwd)"

# Stash any local changes
echo "💾 Stashing local changes..."
git stash push -m "Local changes before CLI update fix" 2>/dev/null || echo "ℹ️  No local changes to stash"

# Pull latest changes
echo "⬇️  Pulling latest updates..."
git pull origin main

# Verify the syntax fix
echo "🔍 Verifying CLI syntax fix..."
if grep -q "console console.print" pisecure/cli_fixed.py; then
    echo "❌ Error: Syntax error still present in cli_fixed.py"
    exit 1
else
    echo "✅ Syntax error fixed - no duplicate console statements"
fi

# Activate virtual environment and test
echo "🐍 Testing CLI..."
source pisecure_env/bin/activate

if pisecure --help >/dev/null 2>&1; then
    echo "✅ CLI working successfully!"
    echo ""
    echo "🎉 PiSecure CLI is now fully functional!"
    echo ""
    echo "Available commands:"
    pisecure --help | head -20
else
    echo "❌ CLI still has issues"
    exit 1
fi

echo ""
echo "📊 Repository Status:"
echo "Latest commit: $(git log --oneline -1)"
echo ""
echo "🚀 Your PiSecure installation is updated and ready!"
echo ""
echo "Test commands:"
echo "  pisecure status              # Blockchain status"
echo "  pisecure update-check --git  # Check for updates"
echo "  python mining-console.py     # Interactive mining console"