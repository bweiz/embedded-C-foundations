// Another interview type question, although I haven't yet seen this in an interview
//
//  The buffer stores int values.
//  FIFO order.
//  Static allocation only.
//  No dynamic memory.
//  rb_push() returns false if the buffer is full.
//  rb_pop() returns false if the buffer is empty or out == NULL.
//  rb_peek() reads the oldest value without removing it.
//  rb_count() returns the number of currently stored items.
//  rb_clear() resets the buffer to empty.
//  Must wrap correctly at the end of the array.
//
//
//

#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>

#define RB_CAPACITY 8

static int buffer[RB_CAPACITY];
static size_t head = 0;
static size_t tail = 0;
static size_t count = 0;

void rb_init(void) {
 
    head = 0;
    tail = 0;
    count = 0;
}

bool rb_push(int value) {

    if (tail == RB_CAPACITY) {
        return false;
    }
    
    buffer[tail] = value;
    tail = (tail + 1) % RB_CAPACITY;
    count++;

    return true;
}

bool rb_pop(int *out) {
    if (count == 0) {
        return false;
    }
    
    if (out == NULL) {
        return false;
    }

    *out = buffer[head];
    head = (head + 1) % RB_CAPACITY;
    count--;
    
    return true;

}

bool rb_peek(int *out) {
    *out = buffer[head];
    return true;
}

size_t rb_count(void) {
    return count;
}

void rb_clear(void) {
    rb_init();
}
