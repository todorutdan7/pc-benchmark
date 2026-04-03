#include "GPUBenchmark.h"

#define NOMINMAX 

#include <windows.h> 
#include <gl/GL.h>  

#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <chrono>

const std::string mandelbrot_kernel_source = R"(
__kernel void bench_mandelbrot(__global float* output, const int max_iters) {
    
    // get thread idx
    int gid = get_global_id(0);
    
    int width = 4096;
    
    // convert 1D thread idx to 2D pixel coords
    // map to [0,1]
    float x_percent = (float)(gid % width) / width;
    float y_percent = (float)(gid / width) / width;

    float c_re = x_percent * 3.5f - 2.5f;  
    float c_im = y_percent * 2.0f - 1.0f;  

    // iteration: z_n+1 = z_n^2 + c
    float z_re = 0.0f;  // z real part
    float z_im = 0.0f;  // z imaginary part
    
    // iterate zn+1 = zn^2 + c up to max_iters times
    for (int i = 0; i < max_iters; i++) {
       
        float z_re_sq = z_re * z_re;  
        float z_im_sq = z_im * z_im;  
        
        float new_re = (z_re_sq - z_im_sq) + c_re;
        
        float new_im = (2.0f * z_re * z_im) + c_im;
        
        z_re = new_re;
        z_im = new_im;
    }

    output[gid] = z_re * z_re + z_im * z_im;
}
)";

GPUBenchmark::GPUBenchmark() {

}

bool GPUBenchmark::initialize_opencl() {
    try {
        
        // check if openCL present
        std::vector<cl::Platform> platforms;
        cl::Platform::get(&platforms);

        // if no openCL, abort
        if (platforms.empty()) return false;

        // found openCL
        cl::Platform platform = platforms.front();

        // prefer NVIDIA over AMD
        for (const auto& p : platforms) {
            std::string name = p.getInfo<CL_PLATFORM_NAME>();

            if (name.find("NVIDIA") != std::string::npos) {
                platform = p;
                break;  
            }
            else if (name.find("AMD") != std::string::npos) {
                platform = p;
            }
        }

        // hold GPU's found on platform
        std::vector<cl::Device> devices;

        // try to find the GPU
        platform.getDevices(CL_DEVICE_TYPE_GPU, &devices);

        // if not return
        if (devices.empty()) {
            platform.getDevices(CL_DEVICE_TYPE_ALL, &devices);
            if (devices.empty()) return false;  
        }

        // use the first gpu found
        m_device = devices.front();

        // openCL context manages GPU res and memory
        m_context = cl::Context(m_device);

        // a queue for work that is executed on the GPU
        // cl queue profiling enable allows to measure execution time 
        m_queue = cl::CommandQueue(m_context, m_device, CL_QUEUE_PROFILING_ENABLE);

        m_results["device_name"] = m_device.getInfo<CL_DEVICE_NAME>();
    }
    catch (...) {
        return false;
    }

    // initialized succesfully
    return true;
}

void GPUBenchmark::run_tests() {
    
    if (!initialize_opencl()) {
        m_results["error"] = "OpenCL Init Failed";
        return;
    }

    run_mandelbrot_test();
}

void GPUBenchmark::run_mandelbrot_test() {
    try {
        // create the program to be executed
        cl::Program program(m_context, mandelbrot_kernel_source);

        // compile the program 
        if (program.build({ m_device }) != CL_SUCCESS) {
            // if fail return 
            std::string log = program.getBuildInfo<CL_PROGRAM_BUILD_LOG>(m_device);
            m_results["mandelbrot"]["error"] = "Build Error: " + log;
            return;
        }

        // extract compiler function by name 
        cl::Kernel kernel(program, "bench_mandelbrot");

        // parameters
        const int WIDTH = 4096;           
        const int HEIGHT = 4096;          
        // nr of threads
        const int GLOBAL_SIZE = WIDTH * HEIGHT;  
        // max iterations for a pixel 
        const int ITERATIONS = 1000;

        cl::Buffer output_buffer(m_context, CL_MEM_WRITE_ONLY, sizeof(float) * GLOBAL_SIZE);

        kernel.setArg(0, output_buffer);
        kernel.setArg(1, ITERATIONS);


        // warm up run
        m_queue.enqueueNDRangeKernel(kernel, cl::NullRange, cl::NDRange(GLOBAL_SIZE));
        m_queue.finish();  

        double total_time_s = 0.0;

        int passes = 50;

        // run multiple times
        for (int i = 0; i < passes; ++i) {
            cl::Event event;
            // capture start and end timestamps
            m_queue.enqueueNDRangeKernel(
                kernel,
                cl::NullRange,         
                cl::NDRange(GLOBAL_SIZE),  
                cl::NullRange,         
                NULL,                  
                &event                 
            );
            // wait for finish
            m_queue.finish();


            // extract start and end time 
            cl_ulong start = event.getProfilingInfo<CL_PROFILING_COMMAND_START>();

            cl_ulong end = event.getProfilingInfo<CL_PROFILING_COMMAND_END>();

            // convert ns to s and store in total 
            total_time_s += (end - start) / 1.0e9;
        }

        // divide by passes
        double avg_time_s = total_time_s / passes;

        double ops_per_iter = 7.0;

        // operations = pixels × iterations × ops_per_iteration
        double total_ops = (double)GLOBAL_SIZE * (double)ITERATIONS * ops_per_iter;

        // GFLOPS = (total operations / time) / 1 billion
        double gflops = (total_ops / avg_time_s) / 1.0e9;

        m_results["mandelbrot"] = {
            {"time_seconds", avg_time_s},       
            {"gflops", gflops},                 
            {"iterations", ITERATIONS},         
            {"total_threads", GLOBAL_SIZE}      
        };

    }
    catch (const cl::Error& err) {
        m_results["mandelbrot"]["error"] = std::string(err.what()) + " (" + std::to_string(err.err()) + ")";
    }
}

void GPUBenchmark::run_tests(const std::string& mode) {

    if (mode == "all" || mode == "compute") {
        if (!initialize_opencl()) {
            m_results["error"] = "OpenCL Init Failed";
        }
        else {
            run_mandelbrot_test();
        }
    }

    if (mode == "all" || mode == "fps") {
        run_fps_test();
    }
}

LRESULT CALLBACK WndProc(HWND hWnd, UINT message, WPARAM wParam, LPARAM lParam) {
    return DefWindowProc(hWnd, message, wParam, lParam);
}

void GPUBenchmark::run_fps_test() {

    // create a window
    WNDCLASSW wc = { 0 };
    wc.lpfnWndProc = WndProc;                    
    wc.hInstance = GetModuleHandle(NULL);        
    wc.hbrBackground = (HBRUSH)(COLOR_BACKGROUND);  
    wc.lpszClassName = L"SCS_Bench_GL";          
    wc.style = CS_OWNDC;                         

    RegisterClassW(&wc);

    HWND hWnd = CreateWindowW(L"SCS_Bench_GL", L"SCS GPU Benchmark",
        WS_OVERLAPPEDWINDOW | WS_VISIBLE,
        100, 100,    // position
        1280, 960,   // size
        NULL, NULL, GetModuleHandle(NULL), NULL);

    if (!hWnd) {
        m_results["fps_test"]["error"] = "Could not create window";
        return;
    }

    // make it visible
    ShowWindow(hWnd, SW_SHOW);
    UpdateWindow(hWnd);           
    SetForegroundWindow(hWnd);    
    SetFocus(hWnd);               

    HDC hDC = GetDC(hWnd);

    PIXELFORMATDESCRIPTOR pfd = { 0 };
    pfd.nSize = sizeof(pfd);
    pfd.nVersion = 1;

    pfd.dwFlags = PFD_DRAW_TO_WINDOW | PFD_SUPPORT_OPENGL | PFD_DOUBLEBUFFER;
    pfd.iPixelType = PFD_TYPE_RGBA;  
    pfd.cColorBits = 32;             
    pfd.cDepthBits = 24;             

    int format = ChoosePixelFormat(hDC, &pfd);
    SetPixelFormat(hDC, format, &pfd);

    HGLRC hRC = wglCreateContext(hDC);
    wglMakeCurrent(hDC, hRC);

    glEnable(GL_DEPTH_TEST);


    // warm up 
    auto warmup_start = std::chrono::high_resolution_clock::now();

    while (true) {
        auto now = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> elapsed = now - warmup_start;

        if (elapsed.count() > 1.5) break;

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

        glLoadIdentity();

        glRotatef(1.0f, 1.0f, 1.0f, 0.0f);

        glBegin(GL_TRIANGLES);
        for (int i = 0; i < 25000; i++) {
            
            glColor3f((i % 10) / 10.0f, (i % 5) / 5.0f, 1.0f);

            glVertex3f(-0.5f + (i * 0.001f), -0.5f, 0.0f);  
            glVertex3f(0.5f + (i * 0.001f), -0.5f, 0.0f);   
            glVertex3f(0.0f + (i * 0.001f), 0.5f, 0.0f);    
        }
        glEnd();

        SwapBuffers(hDC);

        MSG msg;
        while (PeekMessage(&msg, NULL, 0, 0, PM_REMOVE)) {
            TranslateMessage(&msg);
            DispatchMessage(&msg);
        }
    }

    auto start_time = std::chrono::high_resolution_clock::now();

    long long frame_count = 0;
    double duration = 0.0;

    // run for 5 sec 
    while (true) {
        auto now = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> elapsed = now - start_time;
        duration = elapsed.count();

        if (duration >= 5.0) break;

        glClearColor(0.1f, 0.1f, 0.1f, 1.0f);

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

        glLoadIdentity();
        glRotatef((float)frame_count, 1.0f, 1.0f, 0.0f);

        glBegin(GL_TRIANGLES);
        for (int i = 0; i < 25000; i++) {
            glColor3f((i % 10) / 10.0f, (i % 5) / 5.0f, 1.0f);

            glVertex3f(-0.5f + (i * 0.001f), -0.5f, 0.0f);
            glVertex3f(0.5f + (i * 0.001f), -0.5f, 0.0f);
            glVertex3f(0.0f + (i * 0.001f), 0.5f, 0.0f);
        }
        glEnd();

        SwapBuffers(hDC);

        frame_count++;

        MSG msg;
        while (PeekMessage(&msg, NULL, 0, 0, PM_REMOVE)) {
            TranslateMessage(&msg);
            DispatchMessage(&msg);
        }
    }

    wglMakeCurrent(NULL, NULL);   
    wglDeleteContext(hRC);        
    ReleaseDC(hWnd, hDC);         
    DestroyWindow(hWnd);          

    m_results["fps_test"] = {
        {"total_frames", frame_count},                    
        {"duration_seconds", duration},                   
        {"fps", (double)frame_count / duration},          
        {"description", "OpenGL Rasterization (1k polys/frame)"}  
    };
}

json GPUBenchmark::get_results() const {
    return m_results;
}