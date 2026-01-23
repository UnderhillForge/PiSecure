cmake_minimum_required(VERSION 3.12)
project(pisecure_cpp)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find pybind11
find_package(pybind11 CONFIG REQUIRED)

# Crypto module (SHA-256, validation only)
pybind11_add_module(pisecure_cpp_crypto
    cpp/bindings/pybind_sha256.cpp
    cpp/crypto/sha256.cpp
)

# Consensus module (256-bit arithmetic, PoW)
pybind11_add_module(pisecure_cpp_consensus
    cpp/bindings/pybind_consensus.cpp
    cpp/consensus/uint256.cpp
    cpp/consensus/arith_uint256.cpp
)

# Optional: enable SIMD/ARM optimizations
if (UNIX AND NOT APPLE)
    # Linux: detect ARM and enable NEON/SHA2 where available
    include(CheckCXXCompilerFlag)
    CHECK_CXX_COMPILER_FLAG("-mfpu=neon" COMPILER_SUPPORTS_NEON)
    if (COMPILER_SUPPORTS_NEON)
        target_compile_options(pisecure_cpp_crypto PRIVATE -mfpu=neon)
    endif()
    
    CHECK_CXX_COMPILER_FLAG("-march=armv8-a+sha2" COMPILER_SUPPORTS_SHA2)
    if (COMPILER_SUPPORTS_SHA2)
        target_compile_options(pisecure_cpp_crypto PRIVATE -march=armv8-a+sha2)
    endif()
endif()

# Set output directory for modules
set_target_properties(pisecure_cpp_crypto PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/pisecure"
)
set_target_properties(pisecure_cpp_consensus PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/pisecure"
)

# Create __init__.py for pisecure package
file(WRITE "${CMAKE_BINARY_DIR}/pisecure/__init__.py" "")
