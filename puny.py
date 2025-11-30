#!/usr/bin/env python3
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: python puny.py <filename>")
        sys.exit(1)

    filename = sys.argv[1]
    try:
        with open(filename, "r") as f:
            content = f.read()
        #TODO SPLIT INTO LINES FOR LATER
        print(content, end="")
    except FileNotFoundError:
        print("File not found: {filename})")
        sys.exit(1)
if __name__ == "__main__":
    main()