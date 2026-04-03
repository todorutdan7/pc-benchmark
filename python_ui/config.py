import os
import sys 

REFERENCE_SYSTEM = {

    'cpu_pi_single_time_s': 2.6,
    'cpu_pi_multi_time_s': 0.5,
    'cpu_matrix_single_time_s': 2.1,
    'cpu_matrix_multi_time_s': 0.7,
    'cpu_int_time_s': 0.1,
    'cpu_float_time_s': 0.35,       
    
    'ram_l1_bw': 60.0,   
    'ram_l2_bw': 55.0,   
    'ram_l3_bw': 45.0,    
    'ram_main_bw': 21.0,   
    'ram_latency_ns': 114.0,
    
    'disk_seq_read_iops': 2500,         
    'disk_seq_write_iops': 3300,
    'disk_rand_read_iops': 15000,
    'disk_rand_write_iops': 35000,
    'gpu_fps': 430.0, 
    'gpu_gflops': 3900.0             
}

TEST_DESCRIPTIONS = {
    "cpu": (
        "CPU Benchmark Suite:\n"
        "1. Pi digits Calculation (Multi-core Integration)\n"
        "2. Matrix Multiplication (2048 x 2048)\n"
        "3. Integer Hashing\n"
        "4. Float Math"
    ),
    "ram": (
        "Memory Hierarchy Analysis:\n"
        "1. L1, L2, L3 Cache Bandwidth (Read/Write)\n"
        "2. Main Memory Bandwidth (Linear Access)\n"
        "3. Main Memory Latency (Random Pointer Chasing)"
    ),
    "storage": (
        "Drive Performance Evaluation:\n"
        "1. Sequential Read/Write: Uses 1MB blocks to measure IOPS.\n"
        "2. Random Read/Write: Uses 4KB blocks to measure Input/Output Operations (IOPS)." 
    ),
    "gpu": (
        "Graphics Compute Benchmark:\n"
        "Executes a parallel OpenCL compute kernel. "
        "Generates a 4096x4096 Mandelbrot fractal "
        "with 1000 iterations per pixel to measure GFLOPS, also a 3D FPS TEST to measure FPS."
    )
}

BENCHMARK_ITERATIONS = 5

def get_backend_path():

    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
        
    return os.path.join(base_path, "benchmark_backend.exe")