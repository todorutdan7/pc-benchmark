#ifndef GPU_BENCHMARK_H
#define GPU_BENCHMARK_H
#define CL_HPP_ENABLE_EXCEPTIONS
#define CL_HPP_TARGET_OPENCL_VERSION 120
#define CL_HPP_MINIMUM_OPENCL_VERSION 120
#include "include/json.hpp"
#include "include/opencl.hpp"
using json = nlohmann::json;

class GPUBenchmark {
public:
    GPUBenchmark();
    void run_tests();
    json get_results() const;
    void run_tests(const std::string& mode = "all");


private:
    bool initialize_opencl();
    void run_mandelbrot_test();
    void run_fps_test();
    json m_results;
    cl::Context m_context;
    cl::Device m_device;
    cl::CommandQueue m_queue;
    static const int IMG_WIDTH = 4096;
    static const int IMG_HEIGHT = 4096;
    static const int MAX_ITERATIONS = 1000;
};

#endif