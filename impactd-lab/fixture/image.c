#include "image.h"

static uint32_t read_u32_le(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8)
        | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

image_status_t validate_image(const uint8_t *bytes, size_t length)
{
    if (bytes == NULL) return IMAGE_ERR_NULL;
    if (length < IMAGE_HEADER_SIZE) return IMAGE_ERR_SHORT_HEADER;
    if (read_u32_le(bytes) != IMAGE_MAGIC) return IMAGE_ERR_MAGIC;
    if (read_u32_le(bytes + 4) != IMAGE_VERSION) return IMAGE_ERR_VERSION;

    const uint32_t size = read_u32_le(bytes + 8);
    const uint32_t load = read_u32_le(bytes + 12);
    const uint32_t entry = read_u32_le(bytes + 16);
    if (size == 0 || (uintmax_t)size > (uintmax_t)(length - IMAGE_HEADER_SIZE))
        return IMAGE_ERR_SIZE;
    /* Subtract only after checking bounds: do not form load + size. */
    if (load < IMAGE_MEMORY_START || load >= IMAGE_MEMORY_END)
        return IMAGE_ERR_LOAD_RANGE;
    if (size > IMAGE_MEMORY_END - load) return IMAGE_ERR_LOAD_RANGE;
    if (entry < load || entry - load >= size) return IMAGE_ERR_ENTRY_RANGE;
    return IMAGE_OK;
}
