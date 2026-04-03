#include <iostream>
#include <string>
#include <memory>
#include <algorithm>
#include <vector>
#include <fcntl.h> 
#include <io.h>    
#include "CPUBenchmark.h"
#include "RAMBenchmark.h"
#include "StorageBenchmark.h"
#include "GPUBenchmark.h"
#include "SystemInfo.h"
#include "include/json.hpp"

using json = nlohmann::json;

char* get_cmd_option(char** begin, char** end, const std::string& option) {
    char** itr = std::find(begin, end, option);
    if (itr != end && ++itr != end) {
        return *itr;
    }
    return 0;
}

void print_usage() {
    std::cerr << "Usage: benchmark_backend --test <test_type> [options]" << std::endl;
    std::cerr << "Options:" << std::endl;
    std::cerr << "  --pi_digits <int>    (Default: 100000)" << std::endl;
    std::cerr << "  --matrix_size <int>  (Default: 512)" << std::endl;
    std::cerr << "Note: Thread count is automatically detected using hardware_concurrency" << std::endl;
}

int main(int argc, char* argv[]) {


    _setmode(_fileno(stdout), _O_BINARY);
    setvbuf(stdout, NULL, _IONBF, 0);

    if (argc < 3) {
        print_usage();
        return 1;
    }

    std::string test_type_flag = argv[1];
    if (test_type_flag != "--test") {
        print_usage();
        return 1;
    }
    std::string test_type = argv[2];

    std::string subtest_mode = "all"; 

    char* sub_arg = get_cmd_option(argv, argv + argc, "--subtest");
    if (sub_arg) {
        subtest_mode = sub_arg;
    }

    json final_results;

    int pi_digits = 512000;  
    int matrix_size = 2048;
    
    char* pi_arg = get_cmd_option(argv, argv + argc, "--pi_digits");
    if (pi_arg) {
        try { pi_digits = std::stoi(pi_arg); }
        catch (...) {}
    }

    char* mat_arg = get_cmd_option(argv, argv + argc, "--matrix_size");
    if (mat_arg) {
        try { matrix_size = std::stoi(mat_arg); }
        catch (...) {}
    }


    if (test_type == "all" || test_type == "sysinfo") {
        auto sys_info = std::make_unique<SystemInfo>();
        final_results["sysinfo"] = sys_info->get_all_info();
    }
    if (test_type == "all" || test_type == "cpu") {
        auto cpu_benchmark = std::make_unique<CPUBenchmark>(pi_digits, matrix_size);
        cpu_benchmark->run_tests();
        final_results["cpu"] = cpu_benchmark->get_results();
    }
    if (test_type == "all" || test_type == "ram") {
        auto ram_benchmark = std::make_unique<RAMBenchmark>();
        ram_benchmark->run_tests();
        final_results["ram"] = ram_benchmark->get_results();
    }
    if (test_type == "all" || test_type == "storage") {
        auto storage_benchmark = std::make_unique<StorageBenchmark>("scs_test_file.dat");
        storage_benchmark->run_tests();
        final_results["storage"] = storage_benchmark->get_results();
    }
    if (test_type == "all" || test_type == "gpu") {
        auto gpu_benchmark = std::make_unique<GPUBenchmark>();
        gpu_benchmark->run_tests(subtest_mode);
        final_results["gpu"] = gpu_benchmark->get_results();
    }

    if (test_type != "all" && final_results.empty()) {
        std::cerr << "Error: Unknown test type '" << test_type << "'" << std::endl;
        print_usage();
        return 1;
    }

    std::cout << final_results.dump(4) << std::endl;
    return 0;
}