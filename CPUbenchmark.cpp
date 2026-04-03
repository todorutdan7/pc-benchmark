#include "CPUBenchmark.h"
#include "Timer.h"
#include <iostream>
#include <vector>
#include <thread>
#include <future>
#include <cmath>
#include <numeric>

CPUBenchmark::CPUBenchmark(int pi_digits, int matrix_size)
    : m_matrix_size(matrix_size)  
{
    // nr of hardware threads available on this CPU 
    unsigned int hw_threads = std::thread::hardware_concurrency();

    m_num_threads = (hw_threads > 0) ? hw_threads : 4;

    m_pi_iter_limit = static_cast<long long>(pi_digits) * 5000LL;
}

void CPUBenchmark::run_tests() {
    try {
        run_pi_test_single();

        run_pi_test_multi();

        run_matrix_test_single();

        run_matrix_test_multi();

        run_integer_hashing_single();

        run_float_math_single();
    }
    catch (const std::exception& e) {
        m_results["error"] = e.what();
    }
}

json CPUBenchmark::get_results() const {
    return m_results;
}

void CPUBenchmark::run_pi_test_single() {
    
    Timer timer;

    // base of a rectangle
    double step = 1.0 / (double)m_pi_iter_limit;

    double sum = 0.0;

    timer.start();

    for (long long i = 0; i < m_pi_iter_limit; i++) {
        // x is midpoint, i + 0.5 centers 
        // area of a rect base * height 
        double x = (i + 0.5) * step;
            
        sum += 4.0 / (1.0 + x * x);
    }

    timer.stop();

    volatile double dummy = sum * step;

    m_results["pi_single_thread"] = {
        {"time_seconds", timer.get_elapsed_s()},     
        {"iterations", m_pi_iter_limit},             
        {"description", "Single-threaded numerical integration of Pi"}
    };
}

void CPUBenchmark::run_pi_test_multi() {
    Timer timer;

    double step = 1.0 / (double)m_pi_iter_limit;


    // lambda thread syntax, start_idx and end_idx define the range of the processing i-th thread
    auto worker = [&](long long start_idx, long long end_idx) {
        double local_sum = 0.0;

        // compute from start idx to end idx 
        for (long long i = start_idx; i < end_idx; i++) {
            double x = (i + 0.5) * step;
            local_sum += 4.0 / (1.0 + x * x);
        }

        return local_sum;
        };


    // hold local sum of i th thread
    std::vector<std::future<double>> futures;

    // size of one interval 
    long long chunk_size = m_pi_iter_limit / m_num_threads;

    double total_sum = 0.0;

    timer.start();

    for (int t = 0; t < m_num_threads; ++t) {
        // calculate start and end 
        long long start = (long long)t * chunk_size;

        long long end = (t == m_num_threads - 1) ? m_pi_iter_limit : start + chunk_size;

        futures.push_back(std::async(std::launch::async, worker, start, end));
    }

    for (auto& f : futures) {
        total_sum += f.get();
    }

    timer.stop();
    
    volatile double dummy = total_sum * step;

    m_results["pi_multi_thread"] = {
        {"time_seconds", timer.get_elapsed_s()},
        {"iterations", m_pi_iter_limit},
        {"threads", m_num_threads},                  
        {"description", "Multi-threaded numerical integration of Pi"}
    };
}

void CPUBenchmark::run_matrix_test_single() {
    int N = m_matrix_size;

    std::vector<double> A(N * N, 1.0);  
    std::vector<double> B(N * N, 2.0);  
    std::vector<double> C(N * N, 0.0);  

    Timer timer;

    std::vector<double> B_T(N * N);

    // calculate transpose for better caching
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            B_T[j * N + i] = B[i * N + j];
        }
    }

    timer.start();

    for (int i = 0; i < N; ++i) {           
        for (int j = 0; j < N; ++j) {       
            double sum = 0.0;                

            for (int k = 0; k < N; ++k) {
                sum += A[i * N + k] * B_T[j * N + k];
            }

            C[i * N + j] = sum;
        }
    }

    timer.stop();

    m_results["matrix_single_thread"] = {
        {"time_seconds", timer.get_elapsed_s()},
        {"matrix_size", N},                          
        {"description", "Single-threaded Matrix Multiplication"}
    };
}

void CPUBenchmark::run_matrix_test_multi() {
    int N = m_matrix_size;

    std::vector<double> A(N * N, 1.0);
    std::vector<double> B(N * N, 2.0);
    std::vector<double> C(N * N, 0.0);

    Timer timer;

    std::vector<double> B_T(N * N);

    // transpose
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            B_T[j * N + i] = B[i * N + j];
        }
    }

    // array of threads
    std::vector<std::thread> threads;

    // divide matrix rows among threads, x rows per thread
    int rows_per_thread = N / m_num_threads;

    timer.start();

    for (int t = 0; t < m_num_threads; ++t) {
        
        // calculate row ranges
        int start_row = t * rows_per_thread;

        int end_row = (t == m_num_threads - 1) ? N : start_row + rows_per_thread;


        // lambda c++ thread syntax 
        threads.emplace_back([&, start_row, end_row]() {
            for (int i = start_row; i < end_row; ++i) {
                for (int j = 0; j < N; ++j) {
                    double sum = 0.0;

                    for (int k = 0; k < N; ++k) {
                        sum += A[i * N + k] * B_T[j * N + k];
                    }

                    C[i * N + j] = sum;
                }
            }
            });
    }

    // wait for threads to finish work 
    for (auto& t : threads) {
        t.join();
    }

    timer.stop();

    m_results["matrix_multi_thread"] = {
        {"time_seconds", timer.get_elapsed_s()},
        {"matrix_size", N},
        {"threads", m_num_threads},
        {"description", "Multi-threaded Matrix Multiplication"}
    };
}


// bit mixing function 
static inline uint64_t rotl64(uint64_t x, int k) {
    return (x << k) | (x >> (64 - k));
}

void CPUBenchmark::run_integer_hashing_single() {
    
    const int iterations = 50000000;  

    Timer timer;

    uint64_t seed1 = 0x9E3779B97F4A7C15;  // golden ratio
    uint64_t seed2 = 0xBF58476D1CE4E5B9;  // mixing constant

    timer.start();

    for (int i = 0; i < iterations; ++i) {
        
        seed1 += i;

        seed1 = rotl64(seed1, 13);

        seed2 ^= seed1;

        seed2 *= 0xd6e8feb86659fd93;

        seed1 += seed2;

        seed2 = rotl64(seed2, 27);

        seed1 ^= (seed1 >> 33);
    }

    volatile uint64_t res = seed1 + seed2;

    timer.stop();

    m_results["integer_hashing_single"] = {
        {"time_seconds", timer.get_elapsed_s()},
        {"iterations", iterations},
        {"description", "Single-threaded Integer Operations"}
    };
}

void CPUBenchmark::run_float_math_single() {
    
    const int iterations = 10000000;  

    Timer timer;

    timer.start();

    double res = 1.0;

    for (int i = 0; i < iterations; ++i) {
        res = std::sqrt(res + 1.5);

        res = std::sin(res) * std::cos(res);

        res += std::tan(res * 0.001);

        res = std::fabs(res);
    }

    volatile double dummy = res;

    timer.stop();

    m_results["float_math_single"] = {
        {"time_seconds", timer.get_elapsed_s()},
        {"iterations", iterations},
        {"description", "Single-threaded Float Trigonometry & Roots"}
    };
}