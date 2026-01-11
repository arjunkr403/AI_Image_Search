cmake_minimum_required(VERSION 3.10)
project(cpp_preprocess)

# Use C++17
set(CMAKE_CXX_STANDARD 17)

# Find pybind11
find_package(pybind11 REQUIRED)

# Find OpenCV
find_package(OpenCV REQUIRED)

# Create Python module
pybind11_add_module(cpp_preprocess preprocess.cpp)

# Link OpenCV libraries
target_link_libraries(cpp_preprocess PRIVATE ${OpenCV_LIBS})
