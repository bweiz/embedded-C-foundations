

//  static fixed size byte buffer
//  FIFO
//  isr called when byte received
//  read_byte reads oldest byte
//  if full, drop incoming byte
//  if empty, return false
//  if out == NULL, return false
//  no dynamic
//  must wrap correctly
//  good isr practices
//


#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>


#define UART_RX_CAPACITY 16

static uint8_t buffer[UART_RX_CAPACITY];
static size_t head = 0;
static size_t tail = 0;
static size_t count = 0;

void uart_rx_isr(uint8_t byte) {
   // ISR practice: ISR should only enqueue byte, nothing else

    // if full, drop byte
    if (count >= UART_RX_CAPACITY) {
        return;
    }

    buffer[tail] = byte;
    tail = (tail + 1) % UART_RX_CAPACITY;
    count++;
}

bool uart_read_byte(uint8_t *out) {
    // NOTE: ISR technically should be disabled during read, as 
    // race condition is present

    if (out == NULL) {
        return false;   
    }
    
    // if empty...
    if (count == 0) {
        return false;
    }
    
    // read oldest
    *out = buffer[head];
    head = (head + 1) % UART_RX_CAPACITY;
    count--;

    return true;
}

size_t uart_available(void) {
    return count;
}

void uart_clear(void) {
    head  = 0;
    tail  = 0;
    count = 0;
}
