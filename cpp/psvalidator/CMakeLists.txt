cmake_minimum_required(VERSION 3.16)
project(psvalidator VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Compiler flags
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Find dependencies
find_package(nlohmann_json REQUIRED)

# Include directories
include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}/../pisecured/include
)

# Source files
set(PSVALIDATOR_SOURCES
    src/main.cpp
    src/validator.cpp
    src/cli.cpp
    src/monitor_tui.cpp
)

# Build executable
add_executable(psvalidator ${PSVALIDATOR_SOURCES})

# Link libraries
target_link_libraries(psvalidator
    nlohmann_json::nlohmann_json
    pthread
)

# Check if we can link to pisecured's WebSocket client
# This assumes pisecured builds a static library with ws_client
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../pisecured/build/libpisecured.a")
    target_link_libraries(psvalidator
        "${CMAKE_CURRENT_SOURCE_DIR}/../pisecured/build/libpisecured.a"
        websocketpp::websocketpp
        boost_system
        ssl
        crypto
    )
else()
    # If libpisecured.a doesn't exist, we need to build ws_client separately
    # or add the ws_client.cpp directly to our sources
    message(STATUS "Building with inline WebSocket client")
    
    # Add ws_client source
    target_sources(psvalidator PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/../pisecured/src/ws_client.cpp
    )
    
    # Find WebSocketPP
    find_package(websocketpp QUIET)
    if(websocketpp_FOUND)
        target_link_libraries(psvalidator websocketpp::websocketpp)
    else()
        # Try to find it in system paths
        find_path(WEBSOCKETPP_INCLUDE_DIR websocketpp/client.hpp)
        if(WEBSOCKETPP_INCLUDE_DIR)
            target_include_directories(psvalidator PRIVATE ${WEBSOCKETPP_INCLUDE_DIR})
        endif()
    endif()
    
    # Find Boost for WebSocketPP
    find_package(Boost COMPONENTS system QUIET)
    if(Boost_FOUND)
        target_link_libraries(psvalidator Boost::system)
    else()
        target_link_libraries(psvalidator boost_system)
    endif()
    
    # OpenSSL
    find_package(OpenSSL REQUIRED)
    target_link_libraries(psvalidator OpenSSL::SSL OpenSSL::Crypto)
endif()

# Installation
install(TARGETS psvalidator
    RUNTIME DESTINATION bin
)

# Print configuration
message(STATUS "psvalidator configuration:")
message(STATUS "  Build type: ${CMAKE_BUILD_TYPE}")
message(STATUS "  C++ standard: ${CMAKE_CXX_STANDARD}")
message(STATUS "  Install prefix: ${CMAKE_INSTALL_PREFIX}")
