# PiSecure install

Validate with `pisecured` on Debian or Raspberry Pi OS. See the [README](README.md). Mining is the `psminer` binary from GitHub Releases, for Raspberry Pi 2–5 only.

---

## 📦 What Gets Installed

### Core Components
- ✅ **Python environment** - Isolated venv with all dependencies
- ✅ **pisecure CLI** - Main command-line interface
- ✅ **pisecured** - RPC daemon (WebSocket JSON-RPC on port 3144)
- ✅ **pswallet** - Wallet client with smart contract support
- ✅ **psvalidator** - Universal validator (works on ANY platform)

### Platform-Specific
- **psminer** - download the release binary (Raspberry Pi 2–5). It is not built from this tree.

### Dependencies
- Python 3.7+ with cryptography, Flask, Rich, Textual
- C++ build tools (cmake, gcc/g++)
- WebSocket and HTTP clients
- SQLite database
- All requirements from requirements.txt

### Directories Created
- `~/PiSecure/` - Installation directory
- `~/PiSecure/pisecure_env/` - Python virtual environment
- `/var/lib/pisecure/` - Blockchain data storage
- `/etc/pisecure/` - Configuration files

---

## 🖥️ Platform Support

| Platform | pisecure CLI | pisecured | psminer | pswallet | psvalidator |
|----------|-------------|-----------|---------|----------|-------------|
| **Raspberry Pi** | ✅ | ✅ | Release binary | ✅ | ✅ |
| **Linux (x86_64)** | ✅ | ✅ | No | ✅ | ✅ |
| **macOS (Intel/ARM)** | ✅ | ✅ | No | ✅ | ✅ |
| **Windows (WSL)** | ✅ | ✅ | No | ✅ | ✅ |

Mining is the `psminer` release binary on an official Raspberry Pi 2–5. Validation runs on any CPU.

---

## 🎯 Quick Start

After installation:

```bash
# Navigate to install directory
cd ~/PiSecure

# Activate Python environment
source pisecure_env/bin/activate

# Check system status
./pisecure status

# Start RPC daemon (in background or separate terminal)
./pisecured

# psminer: GitHub Releases binary, Raspberry Pi 2–5 only

# On ANY platform: Start validation (earn rewards!)
./psvalidator --rpc ws://127.0.0.1:3144

# Wallet operations
./pswallet balance
./pswallet send <recipient> <amount>

# View blockchain info
./pisecure chain info
```

---

## ⚙️ Installation Process

The installer performs these steps automatically:

1. **System Detection**
   - Detects OS (Linux/macOS/Windows WSL)
   - Identifies Raspberry Pi hardware
   - Checks Python version and tools

2. **Dependency Installation**
   - Installs system packages (cmake, gcc, git, etc.)
   - Updates package manager (apt/yum/dnf/brew)
   - Handles platform-specific requirements

3. **Repository Setup**
   - Clones or updates PiSecure repository
   - Sets up directory structure

4. **Python Environment**
   - Creates isolated virtual environment
   - Installs all Python dependencies
   - Upgrades pip/setuptools/wheel

5. **C++ Components Build**
   - Builds pisecured (RPC daemon)
   - Builds psminer (Pi only)
   - Builds pswallet (wallet client)
   - Builds psvalidator (universal validator)

6. **Configuration**
   - Creates data directories
   - Sets up config files
   - Creates command wrappers

---

## 📋 Requirements

### Minimum System Requirements
- **OS**: Linux (any distro), macOS 10.15+, Windows with WSL2
- **CPU**: 1 GHz+ (multi-core recommended)
- **RAM**: 512 MB minimum, 1 GB+ recommended
- **Disk**: 2 GB free space
- **Python**: 3.7 or higher
- **Network**: Internet connection for installation

### For Mining (Raspberry Pi Only)
- **Hardware**: Genuine Raspberry Pi (Zero, 1, 2, 3, 4, 5)
- **RAM**: 512 MB+ (1 GB+ recommended for Pi 3/4/5)
- **Storage**: 8 GB+ SD card/SSD

### For Validation (Any Platform)
- **CPU**: Any modern processor
- **RAM**: 256 MB+ available
- **Network**: Stable internet connection

---

## 🔧 Troubleshooting

### Installation Fails

**Issue: "Python 3 not found"**
```bash
# Linux/Debian/Ubuntu
sudo apt-get install python3 python3-pip python3-venv

# macOS
brew install python3

# Fedora/RHEL/CentOS
sudo dnf install python3 python3-pip
```

**Issue: "CMake not found"**
```bash
# Linux/Debian/Ubuntu
sudo apt-get install cmake build-essential

# macOS
brew install cmake

# Fedora/RHEL
sudo dnf install cmake gcc-c++
```

**Issue: "Permission denied on /var/lib/pisecure"**
```bash
# Create directories with proper permissions
sudo mkdir -p /var/lib/pisecure /etc/pisecure
sudo chown $USER:$USER /var/lib/pisecure /etc/pisecure
```

### Build Failures

**Issue: "C++ build failed"**
- Check that cmake and gcc/g++ are installed
- Ensure you have at least 500 MB free disk space
- Try building manually:
  ```bash
  cd ~/PiSecure/cpp/pisecured/build
  cmake -DCMAKE_BUILD_TYPE=Release ..
  make -j$(nproc)
  ```

**Issue: "psminer build failed" (not on Pi)**
- This is expected - psminer only builds on Raspberry Pi
- Use psvalidator instead (works everywhere, earns rewards)

### Runtime Issues

**Issue: "Import errors when running pisecure"**
```bash
# Activate virtual environment
cd ~/PiSecure
source pisecure_env/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

**Issue: "pisecured won't start"**
```bash
# Check if port 3144 is already in use
lsof -i :3144  # Linux/macOS
netstat -an | grep 3144  # Windows

# Kill existing process
pkill pisecured
```

---

## 🔐 Security Notes

- The installer creates directories in `/var/lib/pisecure/` and `/etc/pisecure/`
- All Python dependencies are installed in isolated virtual environment
- No root privileges required for running (only for directory creation)
- Wallet private keys stored in `~/.pisecure/wallets/` (create this manually if needed)

---

## 📚 Documentation

After installation, see:
- `~/PiSecure/docs/` - Complete documentation
- `~/PiSecure/docs/getting-started.md` - Getting started guide
- `~/PiSecure/docs/validator-guide.md` - Validator setup
- `~/PiSecure/docs/pisecured-client-guide.md` - RPC daemon usage

---

## 🆘 Support

- **Issues**: https://github.com/UnderhillForge/PiSecure/issues
- **Discussions**: https://github.com/UnderhillForge/PiSecure/discussions
- **Documentation**: `~/PiSecure/docs/README.md`

---

## 🔄 Updating PiSecure

To update an existing installation:

```bash
cd ~/PiSecure
git pull origin main
source pisecure_env/bin/activate
pip install --upgrade -r requirements.txt

# Rebuild C++ components
cd cpp/pisecured/build && cmake .. && make
cd ../../pswallet/build && cmake .. && make
cd ../../psvalidator/build && cmake .. && make
```

Or re-run the installer:
```bash
bash install-oneclick.sh
```

---

## 📄 License

PiSecure is open-source software licensed under MIT License.

---

**Made with ❤️ by the PiSecure Team**
