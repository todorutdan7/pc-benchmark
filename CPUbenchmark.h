#pragma once
#include "include/json.hpp"
#include <cstdint>

using json = nlohmann::json;

class CPUBenchmark {
public:
    CPUBenchmark(int pi_digits, int matrix_size);
    void run_tests();
    json get_results() const;
private:
    long long m_pi_iter_limit;
    int m_matrix_size;
    int m_num_threads;  
    json m_results;
    void run_pi_test_single();
    void run_pi_test_multi();
    void run_matrix_test_single();
    void run_matrix_test_multi();
    void run_integer_hashing_single();
    void run_float_math_single();
};