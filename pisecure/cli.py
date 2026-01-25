#!/usr/bin/env python3
"""
PiSecure CLI - Refactored Entry Point

This is the main CLI entry point. It has been refactored to use the new
modular architecture while maintaining backward compatibility.

The old CLI functionality is preserved in legacy/cli_legacy.py and will be
gradually migrated to the new modular structure in pisecure/cli/.

For now, we delegate to legacy CLI to maintain full compatibility.
"""

import sys

# Import and delegate to legacy CLI during migration phase
try:
    from .legacy.cli_legacy import cli, main
except ImportError:
    # Fallback for direct execution
    from legacy.cli_legacy import cli, main

if __name__ == '__main__':
    main()
