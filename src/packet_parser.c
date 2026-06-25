// From a failed interview question:
//      Valid packet: 
//      Byte1:"$", 0x24
//      Bytes2-5: signed int bytes 
//      Byte6: ";", 0x3B
//
//      Packets can be incomplete
//      Should be able to get valid message from multiple function calls
//      If not valid, do not use
//      Call onParse() on valid packet

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <assert.h>
#include <stdio.h>

static uint8_t packet[6];           // Used to store packets as they come in
static bool inPacket = false;               // Static so persistant across function calls
static size_t idx = 0;

static int parse_count = 0;
static int32_t last_value = 0;

void onParse(int32_t value) {
    parse_count++;
    last_value = value;
}

void resetParser(void)
{
    inPacket = false;
    idx = 0;
}

void resetTestState(void)
{
    resetParser();
    parse_count = 0;
    last_value = 0;
}

void packetParse(const uint8_t *pParse, size_t numBytes) {
    if (pParse == NULL) {
        return;
    }

    
    for (int i = 0; i < numBytes; i++) {
        uint8_t byte = pParse[i];
        
        if (!inPacket) {
            if (byte == 0x24) {
                inPacket = true;
                idx = 0;
                packet[idx++] = byte;           // post increment idx
            }
            continue;
        }

        packet[idx++] = byte;

        if (idx == 6) {                         // End of packet
            if (packet[0] == 0x24 && packet[5] == 0x3B) {
                uint32_t rawPack = 
                    ((uint32_t)packet[1] << 24 |
                     (uint32_t)packet[2] << 16 |
                     (uint32_t)packet[3] << 8  |
                     (uint32_t)packet[4]);
                int32_t value = (int32_t)rawPack;
                onParse(value);
            }
            inPacket = false;
            idx = 0;
        }
    }
}


int main(void) {

    uint8_t goodPack[] =  {0x24, 0x01, 0x02, 0x03, 0x04, 0x3B};
    uint8_t noStart[] =   {0x01, 0x02, 0x03, 0x04, 0x3B};
    uint8_t noEnd[] =     {0x24, 0x01, 0x02, 0x03, 0x04};
    uint8_t halfPack1[] = {0x24, 0x01, 0x02};
    uint8_t halfPack2[] = {0x03, 0x04, 0x3B};

    // Good full packet
    resetTestState();
    packetParse(goodPack, sizeof(goodPack));
    assert(parse_count == 1);
    assert(last_value == 0x01020304);

    // No start byte: should not parse
    resetTestState();
    packetParse(noStart, sizeof(noStart));
    assert(parse_count == 0);

    // Bad end byte: should not parse
    resetTestState();
    packetParse(noEnd, sizeof(noEnd));
    assert(parse_count == 0);

    // Split packet across two calls: should parse once
    resetTestState();
    packetParse(halfPack1, sizeof(halfPack1));
    assert(parse_count == 0);

    packetParse(halfPack2, sizeof(halfPack2));
    assert(parse_count == 1);
    assert(last_value == 0x01020304);

    // NULL pointer: should not crash or parse
    resetTestState();
    packetParse(NULL, 5);
    assert(parse_count == 0);

    // Zero bytes: should not parse
    resetTestState();
    packetParse(goodPack, 0);
    assert(parse_count == 0);


    printf("Success\n");
    return 0;
}
