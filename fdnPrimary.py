# authPrimary.py
import sys
import json


def main():
    for line in sys.stdin:
        print(f"Received data in fdnPrimary: {line}")


if __name__ == '__main__':
    main()
