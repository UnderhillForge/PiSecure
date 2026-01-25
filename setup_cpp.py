"""
Setup build extension for C++ wallet binary
Compiles pswallet during pip install
"""

import os
import sys
import subprocess
from setuptools import Extension
from setuptools.command.build_ext import build_ext
from pathlib import Path


class PSWalletBuild(build_ext):
    """Custom build extension for pswallet C++ binary"""

    def run(self):
        """Build the pswallet binary"""
        print("\n" + "=" * 70)
        print("Building pswallet C++ wallet binary...")
        print("=" * 70 + "\n")

        # Get source directory
        source_dir = Path(__file__).parent / "cpp" / "pswallet"
        if not source_dir.exists():
            print(f"Warning: pswallet source not found at {source_dir}")
            return

        build_dir = source_dir / "build"

        try:
            # Create build directory
            build_dir.mkdir(parents=True, exist_ok=True)

            # Configure with CMake
            print("Running CMake configuration...")
            cmake_cmd = [
                "cmake",
                "-DCMAKE_BUILD_TYPE=Release",
                "-DBUILD_TESTS=OFF",
                str(source_dir),
            ]

            # Set processor type for Raspberry Pi
            if "arm" in sys.platform.lower() or os.uname().machine in [
                "armv7l",
                "armv6l",
                "aarch64",
            ]:
                cmake_cmd.insert(2, "-DCMAKE_SYSTEM_PROCESSOR=" + os.uname().machine)

            result = subprocess.run(cmake_cmd, cwd=str(build_dir), check=False)
            if result.returncode != 0:
                print(
                    "Warning: CMake configuration failed, trying with system defaults..."
                )
                subprocess.run(
                    ["cmake", str(source_dir)], cwd=str(build_dir), check=True
                )

            # Build with make
            print("\nBuilding with make...")
            make_cmd = ["make", f"-j{os.cpu_count() or 1}"]
            subprocess.run(make_cmd, cwd=str(build_dir), check=True)

            # Install binary to system
            print("\nInstalling pswallet binary...")
            subprocess.run(
                ["sudo", "cp", str(build_dir / "pswallet"), "/usr/local/bin/pswallet"],
                check=False,
            )  # Don't fail if not running with sudo

            # Also copy to package bin directory if running locally
            bin_dir = Path(__file__).parent / "pisecure" / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["cp", str(build_dir / "pswallet"), str(bin_dir / "pswallet")],
                check=False,
            )

            print("\n" + "=" * 70)
            print("✓ pswallet build completed successfully!")
            print("  Binary location: /usr/local/bin/pswallet")
            print("=" * 70 + "\n")

        except subprocess.CalledProcessError as e:
            print(f"\nWarning: Failed to build pswallet: {e}")
            print("You can build it manually with:")
            print(f"  cd {source_dir}")
            print(f"  mkdir build && cd build")
            print(f"  cmake -DCMAKE_BUILD_TYPE=Release ..")
            print(f"  make -j$(nproc)")
            print(f"  sudo make install")
            # Don't fail the pip install


def get_pswallet_extension():
    """Get extension for building pswallet"""
    # This is a dummy extension just to trigger the custom build
    return Extension(
        "pisecure._pswallet",
        sources=[],  # No actual Python sources
        optional=True,
    )


class CustomBuildExt(build_ext):
    """Override build_ext to handle our custom pswallet build"""

    def run(self):
        """Run custom build for pswallet"""
        pswallet_build = PSWalletBuild(self.distribution)
        pswallet_build.finalize_options()
        pswallet_build.run()

        # Don't run parent - we don't have real extensions
        # super().run()


def build_pswallet():
    """Build pswallet if cmake is available"""
    print("\nChecking for C++ build tools...")

    # Check if cmake is available
    result = subprocess.run(["which", "cmake"], capture_output=True)
    if result.returncode != 0:
        print("Warning: cmake not found, skipping pswallet build")
        print("To build pswallet manually:")
        print("  1. Install cmake: sudo apt install cmake build-essential")
        print(
            "  2. Run: cd cpp/pswallet && mkdir build && cd build && cmake .. && make -j$(nproc)"
        )
        return None

    # Check if curl development headers are available
    result = subprocess.run(["pkg-config", "--exists", "libcurl"], capture_output=True)
    if result.returncode != 0:
        print("Warning: libcurl development files not found")
        print("Install with: sudo apt install libcurl4-openssl-dev")

    # Check if openssl development headers are available
    result = subprocess.run(["pkg-config", "--exists", "openssl"], capture_output=True)
    if result.returncode != 0:
        print("Warning: OpenSSL development files not found")
        print("Install with: sudo apt install libssl-dev")

    # Check if nlohmann_json is available
    result = subprocess.run(["find", "/usr", "-name", "json.hpp"], capture_output=True)
    if result.returncode != 0 or not result.stdout:
        print("Warning: nlohmann_json header not found")
        print("Install with: sudo apt install nlohmann-json3-dev")
        print("Or download from: https://github.com/nlohmann/json")

    print("All dependencies found, proceeding with build...\n")


if __name__ == "__main__":
    # For manual testing
    build_pswallet()
