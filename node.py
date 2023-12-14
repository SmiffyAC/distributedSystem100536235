import socket
import json
import subprocess
import base64
import threading

import os
import sys


class Node:
    def __init__(self, name):
        # Initialize the client with a name, host, and port
        node_name = socket.gethostname()
        node_ip = socket.gethostbyname(node_name)
        self.name = name
        self.host = node_ip
        self.port = self.find_open_port()

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
        # Connect to the Bootstrap Server
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((bootstrap_host, bootstrap_port))
            # Prepare the client information as JSON
            client_info = {"name": self.name, "ip": self.host, "port": self.port}
            # Send the client information to the Bootstrap Server
            sock.sendall(json.dumps(client_info).encode('utf-8'))
            print(f"Connected to Bootstrap Server and sent info: {client_info}")

            while True:

                response = sock.recv(1024).decode()
                print(f"Received response: {response}")

                if response == "authPrimary":
                    self.handle_auth_primary(sock)

                elif response == "fdnPrimary":
                    self.handle_fdn_primary(sock)

    def handle_auth_primary(self, sock):

        # Send confirmation back to Bootstrap Server
        sock.sendall(b"authPrimary setup complete")

        # Wait for list from server
        client_list_data = sock.recv(1024).decode()
        print(f"Received list data: {client_list_data}")

        client_file_data = sock.recv(1024).decode()
        print(f"Received file data: {client_file_data}")

        # start auth process
        auth_ip = self.host
        auth_port = self.port
        pid = subprocess.Popen([sys.executable, "authPrimary.py", auth_ip, str(auth_port)],
                               creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NEW_CONSOLE).pid

        threading.Thread(target=self.speak_to_auth_primary, args=(client_list_data, client_file_data)).start()
        # node = Node(name="authPrimaryNode", port=9001)
        # threading.Thread(target=node.start_auth_primary_server).start()
        # # Start authPrimary.py process
        # process = subprocess.Popen(["python", "authPrimary.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        #                            text=True)
        #
        # # Send confirmation back to Bootstrap Server
        # sock.sendall(b"authPrimary setup complete")
        #
        # # Wait for list from server
        # list_data = sock.recv(1024).decode()
        # print(f"Received list data: {list_data}")
        #
        # client_file_data = sock.recv(1024).decode()
        # print(f"Received file data: {client_file_data}")
        #
        # process.stdin.write("ACTION1" + list_data)
        # process.stdin.flush()
        #
        # process.stdin.write("ACTION2" + client_file_data)
        # process.stdin.flush()
        #
        # process.stdin.close()

    def speak_to_auth_primary(self, client_list_data, client_file_data):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((self.host, self.port))
            sock.listen()
            print(f"Waiting for authPrimary process on {self.host}:{self.port}")

            while True:
                node, addr = sock.accept()

                response = node.recv(1024).decode()
                print(f"Received response: {response}")

                node.sendall(client_list_data.encode('utf-8'))

                node.sendall(client_file_data.encode('utf-8'))
                # threading.Thread(target=self.handle_node, args=(node, addr)).start()

                response2 = node.recv(1024).decode()
                print(f"Received response: {response2}")

    def handle_fdn_primary(self, sock):

        # Send confirmation back to Bootstrap Server
        sock.sendall(b"fdnPrimary setup complete")

        # Wait for list from server
        client_list_data = sock.recv(1024).decode()
        print(f"Received list data: {client_list_data}")

        number_of_files = int.from_bytes(sock.recv(8), byteorder='big')
        print(f"Expected number of audio files: {number_of_files}")

        file_index = 0

        audio_file_size_list = []
        audio_file_data_list = []

        while file_index < number_of_files:
            # audio_file_size = 0
            # audio_file_size_data = sock.recv(8)
            audio_file_size = int.from_bytes(sock.recv(8), byteorder='big')
            print(f"Audio File size: {audio_file_size}")

            mp3_data = b''
            mp3_data_encoded = ''
            while len(mp3_data) < audio_file_size:
                chunk = sock.recv(min(4096, audio_file_size - len(mp3_data)))
                if not chunk:
                    break
                mp3_data += chunk
                # print(audio_file_size)

            audio_file_size_list.append(audio_file_size)
            print(audio_file_size_list)
            audio_file_data_list.append(mp3_data)
            print(f"File {file_index} received")
            audio_file_size = 0
            file_index += 1

        # audio_file_size_data = sock.recv(8)
        # audio_file_size = int.from_bytes(audio_file_size_data, byteorder='big')
        # print(f"Audio File size: {audio_file_size}")
        #
        # mp3_data = b''
        # mp3_data_encoded = ''
        # while len(mp3_data) < audio_file_size:
        #     chunk = sock.recv(4096)
        #     if not chunk:
        #         break
        #     mp3_data += chunk

        # Convert mp3_data to base64
        # encoded = base64.b64encode(mp3_data).decode('utf-8') + "<END_OF_DATA>"

        # start auth process
        fdn_ip = self.host
        fdn_port = self.port
        pid = subprocess.Popen([sys.executable, "fdnPrimary.py", fdn_ip, str(fdn_port)],
                                   creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NEW_CONSOLE).pid

        threading.Thread(target=self.speak_to_fdn_primary, args=(client_list_data, audio_file_size_list, audio_file_data_list)).start()

        # # node = Node(name="fdnPrimaryNode", port=9001)
        # # threading.Thread(target=node.start_fdn_primary_server).start()
        # # Start fdnPrimary.py process
        # process = subprocess.Popen(["python", "fdnPrimary.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        #                            text=True)
        #
        # # Send confirmation back to Bootstrap Server
        # sock.sendall(b"fdnPrimary setup complete")
        #
        # # Wait for list from server
        # list_data = sock.recv(1024).decode()
        # print(f"Received list data: {list_data}")
        #
        # audio_file_size_data = sock.recv(8)
        # audio_file_size = int.from_bytes(audio_file_size_data, byteorder='big')
        # print(f"Audio File size: {audio_file_size}")
        #
        # mp3_data = b''
        # mp3_data_encoded = ''
        # while len(mp3_data) < audio_file_size:
        #     chunk = sock.recv(4096)
        #     if not chunk:
        #         break
        #     mp3_data += chunk
        #
        # # Convert mp3_data to base64
        # encoded = base64.b64encode(mp3_data).decode('utf-8') + "<END_OF_DATA>"
        #
        # process.stdin.write(encoded)
        # # process.stdin.flush()
        #
        # process.stdin.close()

    def speak_to_fdn_primary(self, client_list_data, audio_file_size_list, audio_file_data_list):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((self.host, self.port))
            sock.listen()
            print(f"Waiting for fdnPrimary process on {self.host}:{self.port}")

            while True:
                node, addr = sock.accept()

                # Print the address and port of the client connected to the node
                print(f"Connected by client at {addr}")

                response = node.recv(1024).decode()
                print(f"Received response: {response}")

                node.sendall(client_list_data.encode('utf-8'))

                number_of_files = len(audio_file_data_list)

                # Tell node how many files to expect
                node.sendall(number_of_files.to_bytes(8, byteorder='big'))

                file = 0

                while file < number_of_files:
                    node.sendall(audio_file_size_list[file].to_bytes(8, byteorder='big'))
                    node.sendall(audio_file_data_list[file])
                    file += 1

                # node.sendall(audio_file_size.to_bytes(8, byteorder='big'))
                #
                # node.sendall(mp3_data)
                # threading.Thread(target=self.handle_node, args=(node, addr)).start()

                response2 = node.recv(1024).decode()
                print(f"Received response: {response2}")

    def start_auth_primary_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))  # Use the Node's host and port
            s.listen()
            print(f"Node acting as Auth Primary listening on {self.host}:{self.port}")
            conn, addr = s.accept()
            with conn:
                print(f"Connected by client at {addr}")
                client_response = conn.recv(1024)
                if client_response == b"token":
                    conn.sendall(b"token handling will be added later")

    def start_fdn_primary_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))  # Use the Node's host and port
            s.listen()
            print(f"Node acting as FDN Primary listening on {self.host}:{self.port}")
            conn, addr = s.accept()
            with conn:
                print(f"Connected by client at {addr}")
                # client_response = conn.recv(1024)
                # if client_response == b"token":
                #     conn.sendall(b"token handling will be added later")


if __name__ == '__main__':
    # Create a client instance with a unique name
    client = Node(name="node")
    # Connect the client to the Bootstrap Server
    # bootstrap_ip = '192.168.0.119'
    # bootstrap_ip = '172.26.61.101'  # IP ADDRESS AT LIBRARY
    bootstrap_ip = open('bootstrap_ip.txt', 'r').read().strip()
    client.connect_to_bootstrap(bootstrap_ip, 50000)
    # node = Node(name="authPrimaryNode", port=9001)
    # node.start_auth_primary_server()
