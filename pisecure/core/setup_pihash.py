#!/usr/bin/env python3
"""
Setup script for building PiHash native extensions

Build instructions:
    # Development build (in-place)
    python pisecure/core/setup_pihash.py build_ext --inplace
    
    # Production build
    python pisecure/core/setup_pihash.py build_ext
    
    # With ARM NEON optimizations
    CFLAGS="-O3 -march=native -mfpu=neon" python pisecure/core/setup_pihash.py build_ext --inplace
"""

from setuptools import setup, Extension
from Cython.Build import cythonize
import numpy as np
import os
import sys

# Compiler flags for optimization
extra_compile_args = [
    "-O3",                    # Maximum optimization
    "-ffast-math",           # Fast math operations
    "-funroll-loops",        # Loop unrolling
]

# ARM-specific optimizations (Raspberry Pi)
if sys.platform == 'linux' and os.uname().machine.startswith('arm'):
    extra_compile_args.extend([
        "-march=native",      # Use native ARM instructions
        "-mfpu=neon",        # Enable NEON SIMD
        "-ftree-vectorize",  # Auto-vectorization
    ])
    print("🚀 Building with ARM NEON optimizations")

extensions = [
    Extension(
        "pisecure.core._pihash_native",
        ["pisecure/core/_pihash_native.pyx"],
        extra_compile_args=extra_compile_args,
        extra_link_args=["-O3"],
        language="c",
    )
]

setup(
    name="pihash_native",
    ext_modules=cythonize(
        extensions,
        compiler_directives={
            'language_level': "3",
            'boundscheck': False,      # Disable bounds checking for speed
            'wraparound': False,        # Disable negative indexing
            'cdivision': True,          # C-style division
            'initializedcheck': False,  # Don't check variable initialization
            'embedsignature': True,     # Include function signatures in docstrings
        },
        annotate=True,  # Generate HTML annotation files for optimization analysis
    ),
)

if __name__ == "__main__":
    print("=" * 70)
    print("PiHash Native Extension Builder")
    print("=" * 70)
    print("This will compile performance-critical PiHash functions to native code.")
    print("Expected speedup: 5-10x for mining operations")
    print()
    print("Requirements:")
    print("  - Cython: pip install cython")
    print("  - GCC/Clang with ARM support")
    print()
    print("Building...")
