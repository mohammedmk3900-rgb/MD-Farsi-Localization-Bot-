cmake_minimum_required(VERSION 3.20)
project(md_native LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(md_native STATIC src/native.cpp)
target_include_directories(md_native PUBLIC include)

add_executable(md_native_probe src/probe.cpp)
target_link_libraries(md_native_probe PRIVATE md_native)
target_include_directories(md_native_probe PRIVATE include)
