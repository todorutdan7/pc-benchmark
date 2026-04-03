cmake_minimum_required(VERSION 3.15)

project(PCBenchmarkBackend CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Threads REQUIRED)
find_package(OpenCL REQUIRED)

add_library(nlohmann_json INTERFACE)
target_include_directories(nlohmann_json INTERFACE "${CMAKE_CURRENT_SOURCE_DIR}/include")

add_executable(benchmark_backend
    Main.cpp
    Timer.h Timer.cpp
    CPUBenchmark.h CPUBenchmark.cpp
    RAMBenchmark.h RAMBenchmark.cpp
    StorageBenchmark.h StorageBenchmark.cpp
    GPUBenchmark.h GPUBenchmark.cpp
    SystemInfo.h SystemInfo.cpp            
)

if(MSVC)
    set_property(TARGET benchmark_backend PROPERTY MSVC_RUNTIME_LIBRARY "MultiThreaded")

    target_compile_options(benchmark_backend PRIVATE /arch:AVX2 /O2 /Oi /fp:fast)
else()
    target_compile_options(benchmark_backend PRIVATE -mavx2 -mfma -O3 -ffast-math)
endif()

target_link_libraries(benchmark_backend 
    PRIVATE 
        Threads::Threads  
        nlohmann_json     
        OpenCL::OpenCL
        opengl32
        user32
        gdi32
)

if (WIN32)
    target_link_libraries(benchmark_backend
        PRIVATE
            wbemuuid
            ole32
            oleaut32
    )
endif()