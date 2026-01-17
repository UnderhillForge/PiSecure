#!/usr/bin/env python3
"""
PiSecure CLI Launcher - Simple Python launcher that works around import issues
"""

import sys
import os

# Add the current directory and repo to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_dir = os.path.join(os.path.dirname(current_dir), 'repo')

sys.path.insert(0, current_dir)
sys.path.insert(0, repo_dir)

def main():
    """Main entry point for the launcher"""
    # Now try to import and run PiSecure CLI
    try:
        from pisecure.cli_fixed import cli
        cli()
    except ImportError as e:
        print(f"Import error: {e}")
        print("Trying alternative import paths...")

        # Try different import approaches
        try:
            # Direct module import
            sys.path.insert(0, '/opt/pisecure/repo')
            from pisecure.cli_fixed import cli
            cli()
        except Exception as e2:
            print(f"Alternative import failed: {e2}")
            print("\nPiSecure CLI is having import issues.")
            print("The web dashboard works perfectly though!")
            print("Access it at: http://localhost:5000")
            sys.exit(1)


if __name__ == '__main__':
    main()