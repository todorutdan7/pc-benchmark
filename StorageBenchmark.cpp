#include "StorageBenchmark.h"
#include "Timer.h"
#include <iostream>
#include <vector>
#include <random>
#include <stdexcept>
#include <windows.h>
#include <string>
#include <thread> 
#include <chrono>

void* aligned_malloc(size_t size, size_t alignment) {
    return _aligned_malloc(size, alignment);
}

void aligned_free(void* ptr) {
    _aligned_free(ptr);
}

const int SEQ_ITERATIONS = 1;

const double RND_DURATION_S = 2.0;

StorageBenchmark::StorageBenchmark(const std::string& test_file_path)
    : m_test_file_path(test_file_path) {
}

StorageBenchmark::~StorageBenchmark() {
    std::remove(m_test_file_path.c_str());  // Delete test file
}

HANDLE OpenTestFile(const char* path, DWORD access, DWORD creation, DWORD flags) {
    HANDLE hFile = INVALID_HANDLE_VALUE;  

    int max_retries = 50;  

    for (int i = 0; i < max_retries; ++i) {
        hFile = CreateFileA(path, access, 0, NULL, creation, flags, NULL);

        if (hFile != INVALID_HANDLE_VALUE) {
            return hFile;  
        }

        DWORD error = GetLastError();

        if (error == ERROR_ACCESS_DENIED || error == ERROR_SHARING_VIOLATION) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));  
        }
        else {
            break;
        }
    }

    return INVALID_HANDLE_VALUE;
}


void FillRandom(char* buffer, size_t size) {
    uint64_t state = 0xABC123;  
    uint64_t* ptr = (uint64_t*)buffer;  
    size_t count = size / sizeof(uint64_t);  

    for (size_t i = 0; i < count; i++) {
        state = state * 6364136223846793005ULL + 1442695040888963407ULL;
        ptr[i] = state;  
    }
}

void StorageBenchmark::run_tests() {
    try {
        run_sequential_write_test();
    }
    catch (const std::exception& e) {
        m_results["sequential_write"]["error"] = e.what();  
    }

    try {
        run_sequential_read_test();
    }
    catch (const std::exception& e) {
        m_results["sequential_read"]["error"] = e.what();
    }

    try {
        run_random_read_iops_test();
    }
    catch (const std::exception& e) {
        m_results["random_read_iops"]["error"] = e.what();
    }

    std::this_thread::sleep_for(std::chrono::milliseconds(500));

    try {
        run_random_write_iops_test();
    }
    catch (const std::exception& e) {
        m_results["random_write_iops"]["error"] = e.what();
    }
}

json StorageBenchmark::get_results() const {
    return m_results;
}

void StorageBenchmark::run_sequential_write_test() {
    // file size in bytes 
    const size_t file_size_bytes = static_cast<size_t>(FILE_SIZE_MB) * 1024 * 1024;

    // how many blocks needed to write entire file
    const size_t num_blocks = file_size_bytes / BLOCK_SIZE_SEQ;

    // buffer aligned to 4096 byte 
    char* buffer = static_cast<char*>(aligned_malloc(BLOCK_SIZE_SEQ, 4096));
    if (!buffer) throw std::runtime_error("Alloc failed");

    // fill buffer with random data 
    FillRandom(buffer, BLOCK_SIZE_SEQ);

    Timer timer;  

    HANDLE hFile = OpenTestFile(m_test_file_path.c_str(), GENERIC_WRITE, CREATE_ALWAYS, FILE_FLAG_NO_BUFFERING | FILE_FLAG_WRITE_THROUGH);

    if (hFile == INVALID_HANDLE_VALUE) {
        aligned_free(buffer); 
        throw std::runtime_error("CreateFile failed (Write)");
    }







    timer.start();  

    // write entire file sequentially, one block at a time
    for (size_t i = 0; i < num_blocks; ++i) {
        DWORD bytes_written;  // bytes written 

        // write one block to file
        if (!WriteFile(hFile, buffer, BLOCK_SIZE_SEQ, &bytes_written, NULL)) {
            // cleanup
            CloseHandle(hFile);  
            aligned_free(buffer);  
            throw std::runtime_error("WriteFile failed");
        }
    }

    timer.stop();  





    // clean up 
    CloseHandle(hFile);
    aligned_free(buffer);

    double total_time = timer.get_elapsed_s();  
    double iops = total_time > 0 ? num_blocks / total_time : 0;  

    m_results["sequential_write"] = {
        {"iops", iops},                      
        {"block_size_used", BLOCK_SIZE_SEQ}, 
        {"time_seconds", total_time}         
    };
}

void StorageBenchmark::run_sequential_read_test() {
    // file size in bytes
    const size_t file_size_bytes = static_cast<size_t>(FILE_SIZE_MB) * 1024 * 1024;

    // how many blocks needed to read entire file
    const size_t num_blocks = file_size_bytes / BLOCK_SIZE_SEQ;

    // buffer aligned to 4096 byte 
    char* buffer = static_cast<char*>(aligned_malloc(BLOCK_SIZE_SEQ, 4096));
    if (!buffer) throw std::runtime_error("Alloc failed");

    // create test file 
    {
        // open file for writing 
        HANDLE hCreate = OpenTestFile(m_test_file_path.c_str(),
            GENERIC_WRITE, CREATE_ALWAYS, 0);

        if (hCreate != INVALID_HANDLE_VALUE) {
            FillRandom(buffer, BLOCK_SIZE_SEQ);  // generate random data

            // write data to file, just for setup
            for (size_t i = 0; i < num_blocks; i++) {
                DWORD w;  // bytes written (unused)
                WriteFile(hCreate, buffer, BLOCK_SIZE_SEQ, &w, NULL);
            }

            CloseHandle(hCreate);  // close file 
        }
    }  

    Timer timer;  

    // open file for reading 
    HANDLE hFile = OpenTestFile(m_test_file_path.c_str(), GENERIC_READ, OPEN_EXISTING, FILE_FLAG_NO_BUFFERING);


    if (hFile == INVALID_HANDLE_VALUE) {
        aligned_free(buffer);
        throw std::runtime_error("CreateFile failed (Read)");
    }

    // warm up read, perform one read to ensure file system is ready
    
    DWORD read;
    ReadFile(hFile, buffer, BLOCK_SIZE_SEQ, &read, NULL);

    // reset file pointer to beginning for actual test
    SetFilePointer(hFile, 0, NULL, FILE_BEGIN);







    timer.start();  


    // read entire file sequentially, one block at a time
    for (size_t i = 0; i < num_blocks; ++i) {
        // read one block from file
        if (!ReadFile(hFile, buffer, BLOCK_SIZE_SEQ, &read, NULL)) {
            break;  // EOF or error 
        }
    }



    timer.stop();  






    // clean up 
    CloseHandle(hFile);
    aligned_free(buffer);

    double total_time = timer.get_elapsed_s();
    double iops = total_time > 0 ? num_blocks / total_time : 0;

    m_results["sequential_read"] = {
        {"iops", iops},                      
        {"block_size_used", BLOCK_SIZE_SEQ}, 
        {"time_seconds", total_time}         
    };
}

void StorageBenchmark::run_random_read_iops_test() {
    // file size and maximum block offset
    const size_t file_size_bytes = static_cast<size_t>(FILE_SIZE_MB) * 1024 * 1024;

    // subtract 1 to ensure we never read past end of file
    const long long max_blocks = (file_size_bytes / BLOCK_SIZE_RND) - 1;

    // buffer for one block (4KB)
    char* buffer = static_cast<char*>(aligned_malloc(BLOCK_SIZE_RND, 4096));
    if (!buffer) throw std::runtime_error("Alloc failed");

    // oepn existing test file for reading 
    // file was created by sequential write test
    HANDLE hFile = OpenTestFile(m_test_file_path.c_str(), GENERIC_READ, OPEN_EXISTING, FILE_FLAG_NO_BUFFERING);

    if (hFile == INVALID_HANDLE_VALUE) {
        aligned_free(buffer);
        throw std::runtime_error("Open failed (Rand Read)");
    }

    // rng for choosing random file positions
    std::mt19937_64 gen(12345);  
    std::uniform_int_distribution<long long> dist(0, max_blocks);  

    long long ops = 0;  
    Timer timer;






    timer.start();  

    // run for fixed duration 
    while (timer.get_elapsed_s() < RND_DURATION_S) {
        // generate block offset
        long long offset = dist(gen) * BLOCK_SIZE_RND;

        // convert offset to LARGE_INTEGER (Windows 64 bit file pointer)
        LARGE_INTEGER li;
        li.QuadPart = offset;

        // seek to random position in file
        SetFilePointerEx(hFile, li, NULL, FILE_BEGIN);

        // read one block at that position
        DWORD bytes;
        ReadFile(hFile, buffer, BLOCK_SIZE_RND, &bytes, NULL);

        ops++;  
    }





    timer.stop();  


    // cleanup
    CloseHandle(hFile);
    aligned_free(buffer);

    m_results["random_read_iops"] = {
        {"iops", ops / timer.get_elapsed_s()},  
        {"operations", ops},                     
    };
}

void StorageBenchmark::run_random_write_iops_test() {
    // file size and maximum block offset
    const size_t file_size_bytes = static_cast<size_t>(FILE_SIZE_MB) * 1024 * 1024;

    // subtract 1 to ensure we never write past end of file
    const long long max_blocks = (file_size_bytes / BLOCK_SIZE_RND) - 1;

    // buffer for one block
    char* buffer = static_cast<char*>(aligned_malloc(BLOCK_SIZE_RND, 4096));
    if (!buffer) throw std::runtime_error("Alloc failed");

    // fill buffer with random data 
    FillRandom(buffer, BLOCK_SIZE_RND);

    // random number generator 
    std::mt19937_64 gen(67890);  
    std::uniform_int_distribution<long long> dist(0, max_blocks);

    // open existing file for writing
    HANDLE hFile = OpenTestFile(m_test_file_path.c_str(), GENERIC_WRITE, OPEN_EXISTING, FILE_FLAG_NO_BUFFERING | FILE_FLAG_WRITE_THROUGH);

    if (hFile == INVALID_HANDLE_VALUE) {
        aligned_free(buffer);
        throw std::runtime_error("Open failed (Rand Write)");
    }

    long long ops = 0;  
    Timer timer;






    timer.start();  

    // run for fixed duration
    while (timer.get_elapsed_s() < RND_DURATION_S) {
        // random block offset
        long long offset = dist(gen) * BLOCK_SIZE_RND;

        // convert to LARGE_INTEGER for 64 bit file positioning
        LARGE_INTEGER li;
        li.QuadPart = offset;

        // seek to random position 
        if (!SetFilePointerEx(hFile, li, NULL, FILE_BEGIN)) break;

        // write one block at that position 
        DWORD bytes;  
        if (!WriteFile(hFile, buffer, BLOCK_SIZE_RND, &bytes, NULL)) break;

        ops++;
    }






    timer.stop();  

    // clean up
    CloseHandle(hFile);
    aligned_free(buffer);

    m_results["random_write_iops"] = {
        {"iops", ops / timer.get_elapsed_s()},  
        {"operations", ops},                     
    };
}