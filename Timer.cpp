#include "Timer.h"

Timer::Timer() : m_is_running(false) {}

void Timer::start() {
    m_start_time = std::chrono::high_resolution_clock::now();
    m_is_running = true;
}

void Timer::stop() {
    m_end_time = std::chrono::high_resolution_clock::now();
    m_is_running = false;
}

double Timer::get_elapsed_ms() const {
    auto end_time = m_is_running ? std::chrono::high_resolution_clock::now() : m_end_time;
    return std::chrono::duration<double, std::milli>(end_time - m_start_time).count();
}

double Timer::get_elapsed_s() const {
    return get_elapsed_ms() / 1000.0;
}