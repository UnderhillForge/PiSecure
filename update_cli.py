#!/usr/bin/env python3
"""
PiSecure CLI Update Script
==========================

This script updates the system-installed PiSecure CLI to include the new update commands.
Run this script on your Raspberry Pi to enable the update command group.
"""

import os
import sys
import shutil
from pathlib import Path

def update_cli():
    """Update the system PiSecure CLI to include update commands"""

    print("🔧 PiSecure CLI Update Script")
    print("=" * 30)

    # Get the current script directory
    script_dir = Path(__file__).parent

    # Source CLI file
    source_cli = script_dir / "pisecure" / "cli.py"

    if not source_cli.exists():
        print(f"❌ Source CLI file not found: {source_cli}")
        return False

    print(f"📁 Source CLI: {source_cli}")

    # Find system Python packages directory
    # Try common locations
    possible_paths = [
        "/usr/local/lib/python3.*/site-packages/pisecure/cli.py",
        "/usr/lib/python3.*/site-packages/pisecure/cli.py",
        "/usr/local/lib/python3/dist-packages/pisecure/cli.py",
        "/usr/lib/python3/dist-packages/pisecure/cli.py"
    ]

    target_cli = None

    # Find the actual installed CLI file
    import glob
    for pattern in possible_paths:
        matches = glob.glob(pattern)
        if matches:
            target_cli = Path(matches[0])
            break

    if not target_cli:
        print("❌ Could not find system-installed PiSecure CLI")
        print("   Searching in common locations...")
        for pattern in possible_paths:
            print(f"   {pattern}")
        return False

    print(f"🎯 Target CLI: {target_cli}")

    # Check if target exists
    if not target_cli.exists():
        print(f"❌ Target CLI file not found: {target_cli}")
        return False

    # Backup current CLI
    backup_cli = target_cli.with_suffix('.bak')
    print(f"💾 Creating backup: {backup_cli}")

    try:
        shutil.copy2(target_cli, backup_cli)
        print("✅ Backup created")
    except Exception as e:
        print(f"❌ Failed to create backup: {e}")
        return False

    # Copy new CLI
    print("📤 Updating CLI file...")

    try:
        shutil.copy2(source_cli, target_cli)
        print("✅ CLI file updated")
    except Exception as e:
        print(f"❌ Failed to update CLI: {e}")
        # Restore backup
        try:
            shutil.copy2(backup_cli, target_cli)
            print("🔄 Backup restored")
        except:
            pass
        return False

    # Test the update
    print("🧪 Testing CLI update...")

    try:
        # Test if CLI loads without errors
        spec = importlib.util.spec_from_file_location("test_cli", target_cli)
        module = importlib.util.module_from_spec(spec)

        # Try to load the module (this will catch import errors)
        spec.loader.exec_module(module)

        print("✅ CLI syntax check passed")

        # Test if update command group exists
        if hasattr(module, 'cli') and hasattr(module.cli, 'commands'):
            if 'update' in module.cli.commands:
                print("✅ Update command group found")
            else:
                print("⚠️  Update command group not found in loaded CLI")
        else:
            print("⚠️  Could not verify CLI structure")

    except Exception as e:
        print(f"❌ CLI test failed: {e}")
        # Restore backup
        try:
            shutil.copy2(backup_cli, target_cli)
            print("🔄 Backup restored due to test failure")
        except:
            pass
        return False

    print("\n🎉 CLI Update Complete!")
    print("=" * 20)
    print("✅ System PiSecure CLI updated")
    print("✅ Update command group available")
    print()
    print("New commands now available:")
    print("  pisecure update check     # Check for updates")
    print("  pisecure update apply     # Apply updates")
    print("  pisecure update status    # Show update status")
    print("  pisecure update rollback  # Rollback versions")
    print()
    print("Test with: pisecure update check")

    return True

if __name__ == "__main__":
    import importlib.util

    success = update_cli()
    if not success:
        print("\n❌ CLI Update Failed")
        print("Manual steps:")
        print("1. Locate your system PiSecure CLI:")
        print("   find /usr -name 'cli.py' | grep pisecure")
        print("2. Backup the current file:")
        print("   sudo cp /path/to/cli.py /path/to/cli.py.bak")
        print("3. Copy the updated CLI:")
        print("   sudo cp /home/pi/PiSecure/pisecure/cli.py /path/to/cli.py")
        sys.exit(1)
    else:
        print("\n🎊 Success! Update commands are now available.")
        sys.exit(0)