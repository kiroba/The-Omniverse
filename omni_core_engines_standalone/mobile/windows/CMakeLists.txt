cmake_minimum_required(VERSION 3.14)
project(omni_core_engines_standalone LANGUAGES CXX)

set(BINARY_NAME "omni_core_engines_standalone")

set(FLUTTER_MANAGED_DIR "${CMAKE_CURRENT_SOURCE_DIR}/flutter")
include("${FLUTTER_MANAGED_DIR}/generated_plugins.cmake" OPTIONAL)

add_subdirectory(runner)
