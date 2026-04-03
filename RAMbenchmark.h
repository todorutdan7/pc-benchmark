#pragma once
#include <vector>
#include <string>
#include <map>
#include "json.hpp" 

using json = nlohmann::json;

class RAMBenchmark {
public:
    RAMBenchmark();
    void run_tests();
    json get_results() const;

private:
    const size_t SIZE_RAM = 512 * 1024 * 1024;
    const size_t SIZE_L3 = 8 * 1024 * 1024;
    const size_t SIZE_L2 = 256 * 1024;
    const size_t SIZE_L1 = 32 * 1024;

    std::vector<uint64_t> m_buffer;
    json m_results;

    json run_transfer_test(size_t chunk_size_bytes, const std::string& label, int iterations);
    void run_ram_latency_test();
};