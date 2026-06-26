

// 32-bit ms system tick counter
// wraps from 0xFFFFFFFF back to 0
//
//  return true if at least timeout_ms ms have elapsed since start_ms
//  return false otherwise
//  if timeout_ms == 0, return true

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

bool has_timed_out(uint32_t now_ms,
                   uint32_t start_ms,
                   uint32_t timeout_ms)
{
    // unsigned int: subtraction handles wrap around
    // addition is implementation defined, so not guaranteed

    return (uint32_t)(now_ms - start_ms) >= timeout_ms;
}
