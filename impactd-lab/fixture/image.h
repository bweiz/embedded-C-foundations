#ifndef IMPACTD_IMAGE_H
#define IMPACTD_IMAGE_H
#include <stddef.h>
#include <stdint.h>

#define IMAGE_HEADER_SIZE 20u
#define IMAGE_MAGIC UINT32_C(0xCD)
#define IMAGE_VERSION UINT32_C(1)
#define IMAGE_MEMORY_START UINT32_C(0x08010000)
#define IMAGE_MEMORY_END UINT32_C(0x08050000)

typedef enum {
    IMAGE_OK = 0,
    IMAGE_ERR_NULL,
    IMAGE_ERR_SHORT_HEADER,
    IMAGE_ERR_MAGIC,
    IMAGE_ERR_VERSION,
    IMAGE_ERR_SIZE,
    IMAGE_ERR_LOAD_RANGE,
    IMAGE_ERR_ENTRY_RANGE
} image_status_t;

/* length includes the header. Caller guarantees length readable bytes.
 * Trailing bytes are permitted. This validates structure, not authenticity. */
image_status_t validate_image(const uint8_t *bytes, size_t length);
#endif
