#  I NEED TO CONNECT BACK TO THE NODE THAT JUST CREATED ME USING THE IP AND PORT PASSED TO ME.
#  THEN ONCE A CONNECTION HAS BEEN MADE I NEED TO LISTEN TO RECEIVE SOMETHING.

import socket
import sys


def main(node_ip, node_port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((node_ip, node_port))
        # Ready to receive data
        print("Connected to node at " + node_ip + ":" + str(node_port))
        # response = s.recv(1024).decode()
        # print("Received response: " + response)
        # while True:
        #     data = s.recv(1024)
        #     if data:
        #         # Process received data
        #         print("Received:", data.decode())
        #         # Send response

        while True:
            s.sendall(b"fdnPrimary process has been created")

            client_list_data = s.recv(1024).decode()
            print(f"Received list data: {client_list_data}")

            ################################################################################

            number_of_files = int.from_bytes(s.recv(8), byteorder='big')
            print(f"Expected number of audio files: {number_of_files}")

            file = 0

            audio_file_size_list = []
            audio_file_data_list = []

            while file < number_of_files:
                audio_file_size_data = s.recv(8)
                audio_file_size = int.from_bytes(audio_file_size_data, byteorder='big')
                print(f"Audio File size: {audio_file_size}")

                mp3_data = b''
                mp3_data_encoded = ''
                while len(mp3_data) < audio_file_size:
                    chunk = s.recv(min(4096, audio_file_size - len(mp3_data)))
                    if not chunk:
                        break
                    mp3_data += chunk

                audio_file_size_list.append(audio_file_size)
                audio_file_data_list.append(mp3_data)

            # audio_file_size_data = s.recv(8)
            # audio_file_size = int.from_bytes(audio_file_size_data, byteorder='big')
            # print(f"Audio File size: {audio_file_size}")
            #
            # mp3_data = b''
            # mp3_data_encoded = ''
            # while len(mp3_data) < audio_file_size:
            #     chunk = s.recv(4096)
            #     if not chunk:
            #         break
            #     mp3_data += chunk
            #
            # print(f"Received mp3 file data")

            s.sendall(b"I have received the data")


if __name__ == '__main__':
    # if len(sys.argv) != 3:
    #     print("Usage: python authPrimary.py <Node IP> <Node Port>")
    #     sys.exit(1)

    main(sys.argv[1], int(sys.argv[2]))

# ... [rest of the authPrimary.py script] ...
