cmake_minimum_required(VERSION 3.12)
project(pisecured VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Threads REQUIRED)
find_package(OpenSSL REQUIRED)

include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}/../hw
    ${CMAKE_CURRENT_SOURCE_DIR}/../crypto
    ${CMAKE_CURRENT_SOURCE_DIR}/../common
    ${OPENSSL_INCLUDE_DIR}
)

# libwebsockets (via pkg-config)
find_package(PkgConfig)
pkg_check_modules(LWS REQUIRED libwebsockets)
if (LWS_FOUND)
    include_directories(${LWS_INCLUDE_DIRS})
    link_directories(${LWS_LIBRARY_DIRS})
    add_definitions(${LWS_CFLAGS_OTHER})
else()
    message(WARNING "libwebsockets not found via pkg-config; build may fail. Install libwebsockets-dev.")
endif()

set(PISECURED_SOURCES
    src/main.cpp
    src/daemon.cpp
    src/config.cpp
    src/storage.cpp
    src/p2p.cpp
    src/rpc.cpp
    src/chain_rpc.cpp
    src/validator_purse.cpp
    src/ws_server.cpp
    ../hw/pihash.cpp
    ../crypto/sha256.cpp
    ../common/release_update.cpp
)

add_executable(pisecured ${PISECURED_SOURCES})
target_compile_definitions(pisecured PRIVATE PISECURE_RELEASE="0.2.9")

target_link_libraries(pisecured
    Threads::Threads
    OpenSSL::SSL
    OpenSSL::Crypto
    ${LWS_LIBRARIES}
)

install(TARGETS pisecured DESTINATION /usr/local/bin)

if(NOT CMAKE_CROSSCOMPILING)
    set(PISECURED_TEST_SOURCES ${PISECURED_SOURCES})
    list(REMOVE_ITEM PISECURED_TEST_SOURCES src/main.cpp)
    add_executable(header_frame_test tests/header_frame_test.cpp ${PISECURED_TEST_SOURCES})
    target_compile_definitions(header_frame_test PRIVATE PISECURE_RELEASE="0.2.9")
    target_link_libraries(header_frame_test
        Threads::Threads
        OpenSSL::SSL
        OpenSSL::Crypto
        ${LWS_LIBRARIES}
    )
    add_executable(retarget_test tests/retarget_test.cpp)
endif()

if(CMAKE_BUILD_TYPE STREQUAL "Release")
    set_target_properties(pisecured PROPERTIES
        COMPILE_FLAGS "-O3 -DNDEBUG"
    )
endif()

message(STATUS "pisecured configured for ${CMAKE_SYSTEM_PROCESSOR}")
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
