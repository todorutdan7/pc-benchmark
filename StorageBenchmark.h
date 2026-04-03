#ifndef STORAGE_BENCHMARK_H
#define STORAGE_BENCHMARK_H

#include "include/json.hpp"
#include <string>
#include <vector>
#include <cstdint>

using json = nlohmann::json;

class StorageBenchmark {
public:
    StorageBenchmark(const std::string& test_file_path = "benchmark_test_file.tmp");
    ~StorageBenchmark();

    void run_tests();
    json get_results() const;

private:
    void run_sequential_write_test();
    void run_sequential_read_test();
    void run_random_read_iops_test();
    void run_random_write_iops_test();


    json m_results;
    std::string m_test_file_path;

    static const size_t FILE_SIZE_MB = 1024; 
    static const size_t BLOCK_SIZE_SEQ = 1 * 1024 * 1024;
    static const size_t BLOCK_SIZE_RND = 4 * 1024; 
    static const int RANDOM_TEST_DURATION_S = 10; 
};

#endif 