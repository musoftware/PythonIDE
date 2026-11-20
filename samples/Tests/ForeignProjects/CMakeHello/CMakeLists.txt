cmake_minimum_required(VERSION 3.16)
project(CMakeHello VERSION 1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# a small library + the program that uses it
add_library(greet STATIC src/greet.cpp)
target_include_directories(greet PUBLIC include)

add_executable(hello src/main.cpp)
target_link_libraries(hello PRIVATE greet)

enable_testing()
add_test(NAME hello_runs COMMAND hello --test)
