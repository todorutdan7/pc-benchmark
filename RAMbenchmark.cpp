#include "RAMBenchmark.h"
#include "Timer.h" 
#include <iostream>
#include <numeric>
#include <random>
#include <algorithm>
#include <vector>
#include <atomic> 
#include <thread>
#include <chrono>

#ifdef _MSC_VER
#include <intrin.h>  
#endif

template <class T>
__forceinline void do_not_optimize(T const& value) {
    volatile T const* p = &value;  
    (void)*p;                      
    std::atomic_signal_fence(std::memory_order_seq_cst);  
}

__forceinline void clobber_memory() {
    std::atomic_signal_fence(std::memory_order_seq_cst);  

#ifdef _MSC_VER
    _ReadWriteBarrier();  
#endif
}

RAMBenchmark::RAMBenchmark() {
    m_buffer.resize(SIZE_RAM / sizeof(uint64_t));

    std::fill(m_buffer.begin(), m_buffer.end(), 1);
}

void RAMBenchmark::run_tests() {

    // warmup 
    volatile uint64_t warmup_sum = 0;

    for (size_t i = 0; i < 2000000; i++) {
        warmup_sum += m_buffer[i % m_buffer.size()];  
    }

    do_not_optimize(warmup_sum);


    // L1 Cache: 32KB, very fast, many iterations
    m_results["l1_cache"] = run_transfer_test(SIZE_L1, "L1 Cache (32KB)", 400000);

    // L2 Cache: 256KB, slower than L1, fewer iterations 
    m_results["l2_cache"] = run_transfer_test(SIZE_L2, "L2 Cache (256KB)", 100000);

    // L3 Cache: 8MB, fewer iterations
    m_results["l3_cache"] = run_transfer_test(SIZE_L3, "L3 Cache (8MB)", 20000);

    // Main RAM: 512MB, slowest, very few iterations
    m_results["main_memory"] = run_transfer_test(SIZE_RAM, "Main RAM (512MB)", 50);

    // latency test 
    run_ram_latency_test();
}

json RAMBenchmark::get_results() const {
    return m_results;
}

json RAMBenchmark::run_transfer_test(size_t chunk_size_bytes, const std::string& label, int iterations) {
  
    // calculate nr of elements
    size_t elements = chunk_size_bytes / sizeof(uint64_t);

    elements = (elements / 8) * 8;

    Timer timer;  




    // write test 
    timer.start();

    // repeat the entire write operation 'iterations' times
    for (int k = 0; k < iterations; ++k) {
        // write to memory in chunks of 8 elements
        for (size_t i = 0; i < elements; i += 8) {
            m_buffer[i] = i + k;       
            m_buffer[i + 1] = i + k;   
            m_buffer[i + 2] = i + k;   
            m_buffer[i + 3] = i + k;   
            m_buffer[i + 4] = i + k;   
            m_buffer[i + 5] = i + k;   
            m_buffer[i + 6] = i + k;   
            m_buffer[i + 7] = i + k;   
        }
        clobber_memory();
    }


    timer.stop();







    // write bandwidth
    double time_write = timer.get_elapsed_s();  
    double total_bytes_rw = (double)chunk_size_bytes * (double)iterations;  
    double bw_write = (total_bytes_rw / time_write) / 1e9;  

    // warmup run

    uint64_t warmup_sum = 0;
    for (size_t i = 0; i < elements && i < 1000; ++i)
        warmup_sum += m_buffer[i];  
    do_not_optimize(warmup_sum);  





    // read test 
    timer.start();

    uint64_t sum0 = 0, sum1 = 0, sum2 = 0, sum3 = 0;

    // repeat the entire read operation 'iterations' times
    for (int k = 0; k < iterations; ++k) {
        // read from memory in chunks of 4 elements
        for (size_t i = 0; i < elements; i += 4) {
            sum0 += m_buffer[i];       
            sum1 += m_buffer[i + 1];   
            sum2 += m_buffer[i + 2];   
            sum3 += m_buffer[i + 3];   
        }
    }

    do_not_optimize(sum0 + sum1 + sum2 + sum3);

    timer.stop();






    // read bandwidth
    double time_read = timer.get_elapsed_s();  
    double bw_read = (total_bytes_rw / time_read) / 1e9;  

    return {
        {"label", label},                      
        {"write_bandwidth_gbs", bw_write},     
        {"read_bandwidth_gbs", bw_read},       
    };
}


void RAMBenchmark::run_ram_latency_test() {
    // number of elements in the buffer
    size_t elements = SIZE_RAM / sizeof(uint64_t);

    // array containing all valid positions (0, 1, 2, ..., elements-1)
    std::vector<size_t> indices(elements);
    std::iota(indices.begin(), indices.end(), 0);  // fill with 0, 1, 2, 3, ...

    // shuffle indices randomly to create unpredictable access

    std::mt19937 gen(12345);  
    std::shuffle(indices.begin(), indices.end(), gen);  

    // circular linked list using the indices
    // each buffer element stores the index of the next element to access
    for (size_t i = 0; i < elements - 1; ++i) {
        m_buffer[indices[i]] = indices[i + 1];  
    }
    // close the loop, last element points back to first
    m_buffer[indices[elements - 1]] = indices[0];

    // number of pointer dereferences to perform 
    const size_t STEPS = 20000000;

    // starting pos 
    size_t current = indices[0];

    Timer timer;

    // clear indices array
    indices.clear();          
    indices.shrink_to_fit();  

    std::this_thread::sleep_for(std::chrono::milliseconds(100));

    



    
    timer.start();

    // each iteration depends on the previous one
    for (size_t k = 0; k < STEPS; ++k) {
        current = m_buffer[current];  // load next index from current position
        // CPU must wait for this load to complete before next iteration can begin
    }



    timer.stop();








    do_not_optimize(current);

    double total_time_ns = timer.get_elapsed_s() * 1e9;  
    double latency_ns = total_time_ns / (double)STEPS;   

    m_results["ram_latency"] = {
        {"test_type", "pointer_chasing_random"},  
        {"steps_performed", STEPS},                
        {"avg_latency_ns", latency_ns}            
    };
}
