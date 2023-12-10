import sys
import json
import base64


def main():
    # for line in sys.stdin:
    #     if line.startswith("ACTION1:"):
    #         data = line[len("ACTION1:"):].strip()
    #         perform_action_1(data)
    #     elif line.startswith("ACTION2:"):
    #         data = line[len("ACTION2:"):].strip()
    #         perform_action_2(data)
    #     else:
    #         data += line
    #         if data.endswith("<END_OF_DATA>"):
    #             data = data[:len(data) - len("<END_OF_DATA>")]
    #             perform_action_2(data)
    #             break
    #
    #         data = line
    #         perform_action_2(data)
    data = ""
    while True:
        line = sys.stdin.read(1)  # Read one character at a time
        if not line:
            break
        data += line
        if data.endswith("<END_OF_DATA>"):  # Check for delimiter
            data = data[:-13]  # Remove delimiter
            perform_action_2(data)
            break


def perform_action_1(data):
    print(f"Performing action 1 with data: {data}")


def perform_action_2(data):
    try:
        audio_binary_data = base64.b64decode(data)
        with open('received_glossy.mp3', 'wb') as file:
            file.write(audio_binary_data)
        # Rest of your code for playing the audio...
    except Exception as e:
        print(f"Error decoding base64 data: {e}")



if __name__ == '__main__':
    main()
