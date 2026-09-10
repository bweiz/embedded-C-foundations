#include "image.h"
#include <stdio.h>
#include <string.h>

static void put_u32_le(uint8_t *p, uint32_t value)
{
    for (unsigned i = 0; i < 4; ++i) p[i] = (uint8_t)(value >> (8u * i));
}

static void valid_image(uint8_t *bytes)
{
    memset(bytes, 0, 24);
    put_u32_le(bytes, IMAGE_MAGIC);
    put_u32_le(bytes + 4, IMAGE_VERSION);
    put_u32_le(bytes + 8, 4);
    put_u32_le(bytes + 12, IMAGE_MEMORY_START);
    put_u32_le(bytes + 16, IMAGE_MEMORY_START);
}

/* Intentionally inadequate assertion, used only by the explicit demo mode.
 * Volatile ensures the validator call remains observable under optimization. */
static int entry_probe(int weak)
{
    uint8_t bytes[24];
    valid_image(bytes);
    put_u32_le(bytes + 16, IMAGE_MEMORY_START + 4);
    volatile image_status_t result = validate_image(bytes, sizeof bytes);
    if (weak) {
        (void)result;
        puts("PASS weak_entry_probe (returned without crashing; rejection unchecked)");
        return 0;
    }
    if (result != IMAGE_ERR_ENTRY_RANGE) {
        fprintf(stderr, "FAIL reject_entry_outside_image: expected %d, got %d\n",
                IMAGE_ERR_ENTRY_RANGE, result);
        return 1;
    }
    puts("PASS reject_entry_outside_image");
    return 0;
}

static unsigned checks;
static unsigned failures;
static void check(const char *name, image_status_t actual, image_status_t expected)
{
    ++checks;
    if (actual != expected) {
        ++failures;
        fprintf(stderr, "FAIL %s: expected %d, got %d\n", name, expected, actual);
    } else {
        printf("PASS %s\n", name);
    }
}

int main(int argc, char **argv)
{
    if (argc == 2 && strcmp(argv[1], "--weak-entry") == 0) return entry_probe(1);
    if (argc == 2 && strcmp(argv[1], "--strong-entry") == 0) return entry_probe(0);
    if (argc != 1) {
        fprintf(stderr, "usage: %s [--weak-entry|--strong-entry]\n", argv[0]);
        return 2;
    }
    uint8_t bytes[25];
    valid_image(bytes);
    check("null", validate_image(NULL, 24), IMAGE_ERR_NULL);
    for (size_t n = 0; n < IMAGE_HEADER_SIZE; ++n) {
        char name[40];
        snprintf(name, sizeof name, "short_header_%zu", n);
        check(name, validate_image(bytes, n), IMAGE_ERR_SHORT_HEADER);
    }
    check("valid", validate_image(bytes, 24), IMAGE_OK);
    bytes[24] = 0xAA;
    check("trailing_bytes_allowed", validate_image(bytes, 25), IMAGE_OK);
    uint8_t unaligned[25];
    memcpy(unaligned + 1, bytes, 24);
    check("unaligned_input", validate_image(unaligned + 1, 24), IMAGE_OK);

    struct test_case {
        const char *name;
        size_t offset;
        uint32_t value;
        image_status_t expected;
    } cases[] = {
        {"bad_magic", 0, 0, IMAGE_ERR_MAGIC},
        {"magic_big_endian_rejected", 0, UINT32_C(0xCD000000), IMAGE_ERR_MAGIC},
        {"unsupported_version", 4, 2, IMAGE_ERR_VERSION},
        {"empty_payload", 8, 0, IMAGE_ERR_SIZE},
        {"oversized_payload", 8, 5, IMAGE_ERR_SIZE},
        {"maximum_size_field", 8, UINT32_MAX, IMAGE_ERR_SIZE},
        {"load_below_memory", 12, IMAGE_MEMORY_START - 1, IMAGE_ERR_LOAD_RANGE},
        {"load_at_memory_end", 12, IMAGE_MEMORY_END, IMAGE_ERR_LOAD_RANGE},
        {"load_near_uint32_max", 12, UINT32_MAX - 1, IMAGE_ERR_LOAD_RANGE},
        {"payload_crosses_memory_end", 12, IMAGE_MEMORY_END - 3, IMAGE_ERR_LOAD_RANGE},
        {"entry_below_payload", 16, IMAGE_MEMORY_START - 1, IMAGE_ERR_ENTRY_RANGE},
        {"entry_at_payload_end", 16, IMAGE_MEMORY_START + 4, IMAGE_ERR_ENTRY_RANGE},
        {"entry_at_last_byte", 16, IMAGE_MEMORY_START + 3, IMAGE_OK},
        {"entry_uint32_max", 16, UINT32_MAX, IMAGE_ERR_ENTRY_RANGE}
    };
    for (size_t i = 0; i < sizeof cases / sizeof cases[0]; ++i) {
        valid_image(bytes);
        put_u32_le(bytes + cases[i].offset, cases[i].value);
        check(cases[i].name, validate_image(bytes, 24), cases[i].expected);
    }
    valid_image(bytes);
    check("truncated_payload", validate_image(bytes, 23), IMAGE_ERR_SIZE);
    put_u32_le(bytes + 12, IMAGE_MEMORY_END - 4);
    put_u32_le(bytes + 16, IMAGE_MEMORY_END - 1);
    check("payload_ends_at_memory_end", validate_image(bytes, 24), IMAGE_OK);
    printf("%u checks, %u failures\n", checks, failures);
    return failures != 0;
}
