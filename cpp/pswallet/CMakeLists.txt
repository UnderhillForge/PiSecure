cmake_minimum_required(VERSION 3.12)
project(pswallet VERSION 1.0.2 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Raspberry Pi specific checks
if(NOT ${CMAKE_SYSTEM_PROCESSOR} MATCHES "arm" AND NOT ${CMAKE_SYSTEM_PROCESSOR} MATCHES "aarch64")
    message(STATUS "Note: pswallet works on all platforms, not just ARM")
endif()

# Find required libraries
find_package(Threads REQUIRED)
find_package(CURL REQUIRED)
find_package(OpenSSL REQUIRED)

# Include directories
include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}/../common
    ${CURL_INCLUDE_DIRS}
    ${OPENSSL_INCLUDE_DIR}
)

# Try to find nlohmann_json
find_package(nlohmann_json 3.2.0 QUIET)
if(NOT nlohmann_json_FOUND)
    # If not found as package, check in system
    message(STATUS "nlohmann_json not found as package, using system headers")
    # Assume it's in standard include path or add manually
    include_directories(/usr/include)
endif()

# Source files
set(PSWALLET_SOURCES
    src/main.cpp
    ../common/release_update.cpp
)

# Main executable
add_executable(pswallet ${PSWALLET_SOURCES})
target_compile_definitions(pswallet PRIVATE PSWALLET_VERSION="${PROJECT_VERSION}" PISECURE_RELEASE="0.2.7")

target_link_libraries(pswallet
    Threads::Threads
    CURL::libcurl
    OpenSSL::Crypto
    OpenSSL::SSL
)

# Installation
install(TARGETS pswallet DESTINATION /usr/local/bin)

# Optional: enable testing
option(BUILD_TESTS "Build test suite" OFF)
if(BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()

# Release optimizations
if(CMAKE_BUILD_TYPE STREQUAL "Release")
    set_target_properties(pswallet PROPERTIES
        COMPILE_FLAGS "-O3 -march=native -DNDEBUG"
    )
endif()

message(STATUS "pswallet configured for ${CMAKE_SYSTEM_PROCESSOR}")
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
