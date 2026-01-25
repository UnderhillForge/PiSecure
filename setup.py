#!/usr/bin/env python3
"""
Setup script for PiSecure - Decentralized Security Framework for Raspberry Pi.

Optimized for one-click install of the modular CLI + background scheduler.
Includes C++ tools: psminer (mining) and pswallet (wallet management + smart contracts).
"""

import os
import sys
import subprocess
from pathlib import Path
from setuptools import find_packages, setup
from setuptools.command.install import install
from setuptools.command.develop import develop


class PostInstallCommand(install):
    """Post-installation hook to build C++ binaries"""

    def run(self):
        install.run(self)
        self._build_cpp_binaries()

    @staticmethod
    def _build_cpp_binaries():
        """Build psminer and pswallet C++ binaries"""
        print("\n" + "=" * 70)
        print("Building C++ components (psminer, pswallet)...")
        print("=" * 70 + "\n")

        base_dir = Path(__file__).parent

        # List of C++ projects to build
        cpp_projects = [
            ("psminer", "Mining client"),
            ("pswallet", "Wallet manager + smart contracts"),
        ]

        for project_name, description in cpp_projects:
            source_dir = base_dir / "cpp" / project_name
            if not source_dir.exists():
                print(f"⊘ {project_name}: source directory not found, skipping")
                continue

            print(f"\n>>> Building {project_name}: {description}")
            print("-" * 70)

            build_dir = source_dir / "build"
            build_dir.mkdir(parents=True, exist_ok=True)

            try:
                # Configure with CMake
                print(f"Configuring {project_name}...")
                cmake_cmd = [
                    "cmake",
                    "-DCMAKE_BUILD_TYPE=Release",
                    "-DBUILD_TESTS=OFF",
                    str(source_dir),
                ]

                # Set processor type if available
                processor = os.uname().machine
                if processor in ["armv7l", "armv6l", "aarch64"]:
                    cmake_cmd.insert(2, f"-DCMAKE_SYSTEM_PROCESSOR={processor}")

                result = subprocess.run(
                    cmake_cmd, cwd=str(build_dir), capture_output=True, text=True
                )
                if result.returncode != 0:
                    print(f"⚠ CMake configuration warning: {result.stderr[:200]}")
                    # Try without processor setting
                    subprocess.run(
                        ["cmake", str(source_dir)],
                        cwd=str(build_dir),
                        capture_output=True,
                        check=False,
                    )

                # Build
                print(f"Compiling {project_name}...")
                cpu_count = os.cpu_count() or 1
                subprocess.run(
                    ["make", f"-j{cpu_count}"],
                    cwd=str(build_dir),
                    capture_output=True,
                    check=True,
                )

                # Try to install
                binary_path = build_dir / project_name
                if binary_path.exists():
                    print(
                        f"✓ {project_name} built successfully ({binary_path.stat().st_size / 1024:.0f} KB)"
                    )

                    # Attempt system installation
                    system_path = f"/usr/local/bin/{project_name}"
                    try:
                        subprocess.run(
                            ["sudo", "cp", str(binary_path), system_path],
                            capture_output=True,
                            check=False,
                        )
                        if Path(system_path).exists():
                            print(f"✓ Installed to {system_path}")
                    except Exception:
                        print(
                            f"⊘ Could not install to system (run with sudo for system-wide install)"
                        )

                    # Also copy to package directory
                    package_bin = base_dir / "pisecure" / "bin"
                    package_bin.mkdir(parents=True, exist_ok=True)
                    subprocess.run(
                        ["cp", str(binary_path), str(package_bin / project_name)],
                        capture_output=True,
                        check=False,
                    )
                    print(f"✓ Installed to {package_bin / project_name}")
                else:
                    print(f"✗ Build failed - binary not found")

            except subprocess.CalledProcessError as e:
                print(f"✗ Failed to build {project_name}: {e}")
                print(
                    f"  Error output: {e.stderr if hasattr(e, 'stderr') else 'See above'}"
                )
                print(f"\nYou can build manually with:")
                print(f"  cd {source_dir}")
                print(f"  mkdir -p build && cd build")
                print(f"  cmake -DCMAKE_BUILD_TYPE=Release ..")
                print(f"  make -j$(nproc)")
                print(f"  sudo make install")
            except Exception as e:
                print(f"✗ Unexpected error building {project_name}: {e}")

        print("\n" + "=" * 70)
        print("C++ build process completed")
        print("=" * 70 + "\n")


# Read version from __init__.py
def get_version():
    with open(os.path.join("pisecure", "__init__.py"), "r") as f:
        for line in f:
            if line.startswith("__version__"):
                return line.split("=")[1].strip().strip("\"'")
    return "0.1.0"


# Read README for long description
def get_long_description():
    with open("README.md", "r", encoding="utf-8") as f:
        return f.read()


setup(
    name="pisecure",
    version=get_version(),
    description="Decentralized Security Framework for Raspberry Pi",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="J Stekervetz",
    author_email="mr_underhill@icloud.com",
    url="https://github.com/UnderhillForge/PiSecure",
    packages=find_packages(),
    include_package_data=True,
    cmdclass={
        "install": PostInstallCommand,
    },
    install_requires=[
        "cryptography>=41.0.0",
        "PyNaCl>=1.5.0",
        "requests>=2.31.0",
        "click>=8.1.0",
        "rich>=13.0.0",
        "textual>=0.41.0",
        "python-dateutil>=2.8.2",
        "psutil>=5.9.0",
        "Flask>=2.3.0",
        "Flask-Cors>=4.0.0",
        "Flask-Limiter>=3.5.0",
        "Flask-SocketIO>=5.3.0",
        "python-socketio>=5.8.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.11.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
            "isort>=5.12.0",
            "pre-commit>=3.5.0",
            "ipykernel>=6.23.0",
            "jupyter>=1.0.0",
            "ipdb>=0.13.0",
            "locust>=2.15.0",
        ],
        "hardware": [
            "RPi.GPIO>=0.7.0",
            "gpiozero>=2.0",
        ],
        "ipfs": [
            "ipfshttpclient>=0.7.0",
        ],
        "tpm": [
            "tpm2-pytss>=1.2.0",
        ],
        "full": [
            "ipfshttpclient>=0.7.0",
            "RPi.GPIO>=0.7.0",
            "gpiozero>=2.0",
            "tpm2-pytss>=1.2.0",
            "asyncio-mqtt>=0.13.0",
            "jsonschema>=4.17.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "pisecure=pisecure.cli_refactored:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: C++",
        "Topic :: Security",
        "Topic :: Security :: Cryptography",
        "Topic :: System :: Hardware",
        "Topic :: Internet :: WWW/HTTP",
    ],
    keywords="raspberry-pi blockchain security iot cryptography hardware-verification mining wallet smart-contracts",
    python_requires=">=3.8",
    project_urls={
        "Bug Reports": "https://github.com/UnderhillForge/PiSecure/issues",
        "Source": "https://github.com/UnderhillForge/PiSecure",
        "Documentation": "https://pisecure.readthedocs.io/",
    },
)
