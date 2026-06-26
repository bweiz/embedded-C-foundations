

// example: parsing binary messages from comm. protocol
// Multi-byte integers transmitted as raw bytes
//
// REQUIREMENTS:
//      false if buf or out is NULL
//      false if not enough bytes from offset
//      never read out of bounds
//
//      don't cast buffer pointer to uint16/32_t
//      must work regardless of CPU endianess
//      must avoid alignment issues
//      for signed 32-bit values, recon. as uint32_t, then cast to int32_t

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

bool read_u16_be(const uint8_t *buf, size_t len, size_t offset, uint16_t *out)
{
    if (buf == NULL || out == NULL) {
        return false;
    }
    // first, check if size and offset are compatible so no Out of Bounds

    if (offset > len || len - offset < 2) {
        return false;
    }

    uint16_t raw = 
        ((uint16_t)buf[offset] << 8) |          // high byte
        ((uint16_t)buf[offset + 1]);            // low byte

    *out = raw;

    return true;  
}

bool read_u16_le(const uint8_t *buf, size_t len, size_t offset, uint16_t *out)
{
    if (buf == NULL || out == NULL) {
        return false;
    }

    if (offset > len || len - offset < 2) {
        return false;
    }

    uint16_t raw = 
        ((uint16_t)buf[offset + 1] << 8) |      // high byte
        ((uint16_t)buf[offset]);                // low byte

    *out = raw;

    return true;
}

bool read_i32_be(const uint8_t *buf, size_t len, size_t offset, int32_t *out)
{
    if (buf == NULL || out == NULL) {
        return false;
    }

    if (offset > len || len - offset < 4) {
        return false;
    }


    uint32_t raw =
        ((uint32_t)buf[offset]     << 24) |     // highest byte
        ((uint32_t)buf[offset + 1] << 16) |
        ((uint32_t)buf[offset + 2] << 8)  |
        ((uint32_t)buf[offset + 3]);            // lowest byte

    *out = (int32_t)raw;

    return true;
}

bool read_i32_le(const uint8_t *buf, size_t len, size_t offset, int32_t *out)
{
    if (buf == NULL || out == NULL) {
        return false;
    }  

    if (offset > len || len - offset < 4) {
        return false;
    }

    uint32_t raw = 
        ((uint32_t)buf[offset + 3] << 24) |     // highest byte
        ((uint32_t)buf[offset + 2] << 16) |
        ((uint32_t)buf[offset + 1] << 8)  |
        ((uint32_t)buf[offset]);                // lowest byte

    *out = (int32_t)raw;

    return true;
}
