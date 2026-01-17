#!/usr/bin/env python3
"""
PiHash Native Extension Build & Installation Script
===================================================

This script automates the building and installation of PiHash native
extensions for maximum mining performance.

Usage:
    # Build native extensions
    python build_pihash_native.py
    
    # Build with verbose output
    python build_pihash_native.py --verbose
    
    # Clean build artifacts
    python build_pihash_native.py --clean
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def check_requirements():
    """Check if all build requirements are installed"""
    print_header("Checking Build Requirements")
    
    requirements = {
        'cython': 'Cython',
        'numpy': 'NumPy',
    }
    
    missing = []
    for module, name in requirements.items():
        try:
            __import__(module)
            print(f"✅ {name}: installed")
        except ImportError:
            print(f"❌ {name}: missing")
            missing.append(name.lower())
    
    if missing:
        print(f"\n⚠️  Missing requirements: {', '.join(missing)}")
        print(f"\nInstall with: pip install {' '.join(missing)}")
        return False
    
    # Check compiler
    try:
        result = subprocess.run(['gcc', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            print(f"✅ GCC: {version}")
        else:
            print("❌ GCC: not found")
            return False
    except FileNotFoundError:
        print("❌ GCC: not found")
        print("\nInstall with: sudo apt-get install build-essential")
        return False
    
    return True

def clean_build():
    """Clean build artifacts"""
    print_header("Cleaning Build Artifacts")
    
    patterns = [
        'pisecure/core/_pihash_native.c',
        'pisecure/core/_pihash_native*.so',
        'pisecure/core/_pihash_native*.html',
        'build/',
        'pisecure/core/__pycache__/',
    ]
    
    for pattern in patterns:
        path = Path(pattern)
        if path.is_file():
            path.unlink()
            print(f"🗑️  Removed: {pattern}")
        elif path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
            print(f"🗑️  Removed: {pattern}")
    
    print("✅ Cleanup complete")

def build_native():
    """Build native extensions"""
    print_header("Building PiHash Native Extensions")
    
    # Change to project root
    os.chdir(Path(__file__).parent.parent.parent)
    
    # Build command
    cmd = [
        sys.executable,
        'pisecure/core/setup_pihash.py',
        'build_ext',
        '--inplace'
    ]
    
    print(f"📦 Build command: {' '.join(cmd)}")
    print()
    
    # Run build
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode == 0:
        print_header("Build Successful! 🎉")
        print("✅ Native extensions compiled successfully")
        print("✅ Expected performance improvement: 5-10x")
        print("\n📝 Note: PiSecure will automatically use native code when available")
        return True
    else:
        print_header("Build Failed ❌")
        print("⚠️  Native extensions failed to compile")
        print("ℹ️  PiSecure will fall back to pure Python (slower but functional)")
        return False

def verify_installation():
    """Verify that native extensions are importable"""
    print_header("Verifying Installation")
    
    try:
        from pisecure.core import pihash
        if pihash.NATIVE_AVAILABLE:
            print("✅ Native extensions: AVAILABLE")
            print(f"✅ Loaded successfully: {pihash._pihash_native}")
            
            # Run quick benchmark
            print("\n🚀 Running quick benchmark...")
            from pisecure.core._pihash_native import benchmark_native
            results = benchmark_native()
            print(f"   Iterations: {results['iterations']}")
            print(f"   Average time: {results['avg_time_ms']:.2f}ms")
            print("✅ Benchmark completed successfully")
            return True
        else:
            print("❌ Native extensions: NOT AVAILABLE")
            if pihash._NATIVE_LOAD_ERROR:
                print(f"   Error: {pihash._NATIVE_LOAD_ERROR}")
            return False
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

def main():
    """Main build process"""
    print_header("PiHash Native Extension Builder")
    print("This will compile performance-critical PiHash functions to native code")
    print("for 5-10x faster mining on Raspberry Pi hardware.")
    
    # Parse arguments
    verbose = '--verbose' in sys.argv
    clean_only = '--clean' in sys.argv
    
    if clean_only:
        clean_build()
        return
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Clean old builds
    clean_build()
    
    # Build native extensions
    if not build_native():
        print("\n⚠️  Build failed but PiSecure will still work (slower)")
        sys.exit(1)
    
    # Verify installation
    if not verify_installation():
        print("\n⚠️  Installation verification failed")
        sys.exit(1)
    
    print_header("Setup Complete! ✅")
    print("Native acceleration is ready for mining.")
    print("\nTo disable native code, set use_native=False when creating PiHash instances.")

if __name__ == '__main__':
    main()
