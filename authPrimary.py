# authPrimary.py
import sys
import json


def main():
    for line in sys.stdin:
        print(f"Received data in authPrimary: {line}")


if __name__ == '__main__':
    main()
