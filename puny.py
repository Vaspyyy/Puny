#!/usr/bin/env python3
import sys ,termios ,tty ,atexit

#def cleanp():
    #TODO RESTORE TERMINAL SETTINGS HERE

def main():
    #TODO SAVE OLD TTY SETTINGS; SET RAW MODE; REGISTER CLEANUP
    print("press q to quit", end="\r\n")
    while True:
        ch = sys.stdin.read(1)
        if ch == "q":
            break
        #TODO PRINT WHATS TYPED WITHOUT ECHOING


if __name__ == "__main__":
    main()