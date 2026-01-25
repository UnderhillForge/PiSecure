# Makefile for psminer
# Convenience wrapper around CMake

.PHONY: all build clean install test help release debug

# Default target
all: release

# Release build (optimized)
release:
	@./build.sh Release

# Debug build
debug:
	@./build.sh Debug

# Build with current configuration
build:
	@if [ -d build ]; then \
		cd build && make -j$$(nproc); \
	else \
		./build.sh Release; \
	fi

# Clean build artifacts
clean:
	@echo "Cleaning build directory..."
	@rm -rf build
	@echo "✓ Clean complete"

# Install (requires sudo)
install:
	@if [ ! -d build ]; then \
		echo "Error: No build directory. Run 'make' first."; \
		exit 1; \
	fi
	@echo "Installing psminer..."
	@cd build && sudo make install
	@echo "✓ Installed to /usr/local/bin/psminer"

# Run tests
test:
	@if [ ! -d build ]; then \
		echo "Error: No build directory. Run 'make' first."; \
		exit 1; \
	fi
	@cd build && ctest -V

# Quick test run (must provide wallet)
run:
	@if [ ! -f build/psminer ]; then \
		echo "Error: psminer not built. Run 'make' first."; \
		exit 1; \
	fi
	@if [ -z "$(WALLET)" ]; then \
		echo "Error: WALLET not set."; \
		echo "Usage: make run WALLET=your_wallet_address"; \
		exit 1; \
	fi
	@echo "Starting psminer..."
	@./build/psminer -w $(WALLET) $(ARGS)

# Show help
help:
	@echo "PiSecure Miner Build System"
	@echo
	@echo "Targets:"
	@echo "  make          - Build release version (default)"
	@echo "  make release  - Build optimized release version"
	@echo "  make debug    - Build debug version"
	@echo "  make build    - Rebuild current configuration"
	@echo "  make clean    - Remove build artifacts"
	@echo "  make install  - Install to /usr/local/bin (requires sudo)"
	@echo "  make test     - Run test suite"
	@echo "  make run      - Quick test run (requires WALLET=address)"
	@echo "  make help     - Show this help"
	@echo
	@echo "Examples:"
	@echo "  make"
	@echo "  make install"
	@echo "  make run WALLET=your_wallet_address"
	@echo "  make run WALLET=your_wallet_address ARGS=\"-t 4 --testnet\""
