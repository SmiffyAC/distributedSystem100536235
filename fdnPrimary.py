import socket
import sys


def main(node_ip, node_port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((node_ip, node_port))
        # Ready to receive data
        print("Connected to node at " + node_ip + ":" + str(node_port))

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

            s.sendall(b"I have received the data")


if __name__ == '__main__':

    main(sys.argv[1], int(sys.argv[2]))

