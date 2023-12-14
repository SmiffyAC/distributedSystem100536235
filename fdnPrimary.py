import socket
import json
import subprocess
import base64
import threading

import os
import sys


class FdnPrimary:
    def __init__(self, name):
        # Initialize the client with a name, host, and port
        node_name = socket.gethostname()
        node_ip = socket.gethostbyname(node_name)
        self.name = name
        self.host = node_ip
        self.port = self.find_open_port()
        print(f"AuthPrimary set up on: {self.host}, Node Port: {self.port}")

    def find_open_port(self):
        # Iterate through the port range to find the first open port
        port_range = (50001, 50010)
        for port in range(port_range[0], port_range[1] + 1):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                if sock.connect_ex((self.host, port)) != 0:
                    # Port is open, use this one
                    return port
        raise Exception("No open ports available in the specified range.")

    def connect_to_bootstrap(self, bootstrap_host, bootstrap_port):
        print(f"FdnPrimary connecting to Bootstrap Server at {bootstrap_host}:{bootstrap_port}")
        # Connect to the Bootstrap Server
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((bootstrap_host, bootstrap_port))
            # Prepare the client information as JSON
            client_info = {"name": self.name, "ip": self.host, "port": self.port}
            # Send the client information to the Bootstrap Server
            sock.sendall(json.dumps(client_info).encode('utf-8'))
            print(f"Connected to Bootstrap Server and sent info: {client_info}")

            while True:

                client_list_data = sock.recv(1024).decode()
                print(f"Received list data: {client_list_data}")

                number_of_files = int.from_bytes(sock.recv(8), byteorder='big')
                print(f"Expected number of audio files: {number_of_files}")

                file = 0

                audio_file_size_list = []
                audio_file_data_list = []

                while file < number_of_files:
                    audio_file_size_data = sock.recv(8)
                    audio_file_size = int.from_bytes(audio_file_size_data, byteorder='big')
                    print(f"Audio File size: {audio_file_size}")

                    mp3_data = b''
                    mp3_data_encoded = ''
                    while len(mp3_data) < audio_file_size:
                        chunk = sock.recv(min(4096, audio_file_size - len(mp3_data)))
                        if not chunk:
                            break
                        mp3_data += chunk

                    audio_file_size_list.append(audio_file_size)
                    print(audio_file_size_list)
                    audio_file_data_list.append(mp3_data)
                    print(f"File {file} received")
                    file += 1


if __name__ == '__main__':
    new_FdnPrimary = FdnPrimary(name="fdnPrimary")

    # Connect the client to the Bootstrap Server
    bootstrap_ip = open('bootstrap_ip.txt', 'r').read().strip()
    new_FdnPrimary.connect_to_bootstrap(bootstrap_ip, 50000)
