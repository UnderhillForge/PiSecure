cmake_minimum_required(VERSION 3.16)
project(PiSecure LANGUAGES CXX)

# The live node and wallet. PiHash stays in cpp/hw and is linked by pisecured.
add_subdirectory(cpp/pisecured)
add_subdirectory(cpp/pswallet)
