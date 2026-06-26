

//  simple embedded controller state machine

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef enum {
    STATE_IDLE,
    STATE_ARMED,
    STATE_RUNNING,
    STATE_FAULT
} State;

typedef enum {
    CMD_ARM,
    CMD_START,
    CMD_STOP,
    CMD_FAULT,
    CMD_RESET
} Command;

static bool valid_state(State state) {

    if (state == STATE_IDLE    ||
        state == STATE_ARMED   ||
        state == STATE_RUNNING ||
        state == STATE_FAULT)     { return true; }

    return false;

}

static bool valid_command(Command command) {

    if (command == CMD_ARM   ||
        command == CMD_START ||
        command == CMD_STOP  ||
        command == CMD_FAULT ||
        command == CMD_RESET)     { return true; }

    return false;

}

State next_state(State current, Command command)
{

    if (!valid_state(current)) {         // Fault if not valid state
        return STATE_FAULT; 
    }

    if (!valid_command(command)) {       // no change in state if invalid command
        if (valid_state(current)) {
            return current;
        } 
        
        return STATE_FAULT;
    }

    switch (current) {
        case STATE_IDLE:
            if (command == CMD_ARM)   { return STATE_ARMED;   }
            if (command == CMD_FAULT) { return STATE_FAULT;   }
            return STATE_IDLE;
            break;
        case STATE_ARMED:
            if (command == CMD_START) { return STATE_RUNNING; }
            if (command == CMD_STOP)  { return STATE_IDLE;    }
            if (command == CMD_FAULT) { return STATE_FAULT;   }
            return STATE_ARMED;
            break;
        case STATE_RUNNING:
            if (command == CMD_STOP)  { return STATE_IDLE;    }
            if (command == CMD_FAULT) { return STATE_FAULT;   }
            if (command == CMD_RESET) { return STATE_FAULT;   }
            return STATE_RUNNING;
            break;
        case STATE_FAULT:
            if (command == CMD_RESET) { return STATE_IDLE;    } 
            return STATE_FAULT; 
            break;
        default:
            return STATE_FAULT;
    }
}
