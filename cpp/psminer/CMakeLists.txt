cmake_minimum_required(VERSION 3.12)
project(psminer VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Raspberry Pi specific checks
if(NOT ${CMAKE_SYSTEM_PROCESSOR} MATCHES "arm" AND NOT ${CMAKE_SYSTEM_PROCESSOR} MATCHES "aarch64")
    message(WARNING "psminer is designed for Raspberry Pi (ARM) platforms. Current: ${CMAKE_SYSTEM_PROCESSOR}")
endif()

# Build options
option(BUILD_TESTS "Build test suite" OFF)
option(ENABLE_HARDWARE_VERIFICATION "Enable strict Pi hardware verification" ON)

# Find required libraries
find_package(Threads REQUIRED)
find_package(Curses REQUIRED)

# Include directories
include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}/../hw
    ${CMAKE_CURRENT_SOURCE_DIR}/../crypto
    ${CMAKE_CURRENT_SOURCE_DIR}/../consensus
    ${CMAKE_CURRENT_SOURCE_DIR}/../util
    ${CURSES_INCLUDE_DIR}
)

# Source files
set(PSMINER_SOURCES
    src/main.cpp
    src/cli.cpp
    src/miner.cpp
    src/monitor_tui.cpp
    src/hardware_verifier.cpp
    src/pihash_adapter.cpp
    src/pins_resolver.cpp
    ../hw/pihash.cpp
    ../hw/videocore_mailbox.cpp
    ../crypto/sha256.cpp
    ../consensus/arith_uint256.cpp
    ../consensus/uint256.cpp
    ../consensus/pow.cpp
)

# Main executable
add_executable(psminer ${PSMINER_SOURCES})

target_link_libraries(psminer
    Threads::Threads
    ${CURSES_LIBRARIES}
    ${CMAKE_DL_LIBS}
)

# Compiler flags for optimization
if(CMAKE_BUILD_TYPE STREQUAL "Release")
    target_compile_options(psminer PRIVATE
        -O3
        -march=native
        -mtune=native
        -flto
    )
    set_target_properties(psminer PROPERTIES
        INTERPROCEDURAL_OPTIMIZATION TRUE
    )
endif()

# ARM-specific optimizations
if(${CMAKE_SYSTEM_PROCESSOR} MATCHES "arm" OR ${CMAKE_SYSTEM_PROCESSOR} MATCHES "aarch64")
    if(${CMAKE_SYSTEM_PROCESSOR} MATCHES "aarch64")
        # 64-bit ARM (ARMv8) - NEON is standard, no -mfpu needed
        target_compile_options(psminer PRIVATE
            -ftree-vectorize
        )
    else()
        # 32-bit ARM (ARMv7) - needs explicit NEON flag
        target_compile_options(psminer PRIVATE
            -mfpu=neon
            -ftree-vectorize
        )
    endif()
endif()

# Installation
install(TARGETS psminer
    RUNTIME DESTINATION bin
)

# Documentation
install(FILES README.md
    DESTINATION share/doc/psminer
)
