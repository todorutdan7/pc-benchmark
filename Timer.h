#ifndef TIMER_H
#define TIMER_H

#include <chrono>

class Timer {
public:
    Timer();
    void start();
    void stop();
    double get_elapsed_ms() const;
    double get_elapsed_s() const;

private:
    std::chrono::time_point<std::chrono::high_resolution_clock> m_start_time;
    std::chrono::time_point<std::chrono::high_resolution_clock> m_end_time;
    bool m_is_running;
};

#endif 