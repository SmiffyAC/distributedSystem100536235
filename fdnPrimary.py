import sys
import json


def main():
    for line in sys.stdin:
        if line.startswith("ACTION1:"):
            data = line[len("ACTION1:"):].strip()
            perform_action_1(data)
        elif line.startswith("ACTION2:"):
            data = line[len("ACTION2:"):].strip()
            perform_action_2(data)


def perform_action_1(data):
    print(f"Performing action 1 with data: {data}")


def perform_action_2(data):
    print(f"Performing action 2 with data: {data}")


if __name__ == '__main__':
    main()
