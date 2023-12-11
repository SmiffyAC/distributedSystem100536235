import socket
import json
import subprocess
import pygame
import base64
import threading


class Node:
    def __init__(self, name, port=9000):
        # Initialize the client with a name, host, and port
        node_name = socket.gethostname()
        node_ip = socket.gethostbyname(node_name)
        self.name = name
        self.host = node_ip
        self.port = port

    def connect_to_bootstrap(self, bootstrap_host, bootstrap_port):
        # Connect to the Bootstrap Server
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((bootstrap_host, bootstrap_port))
            # Prepare the client information as JSON
            client_info = {"name": self.name, "ip": self.host, "port": self.port}
            # Send the client information to the Bootstrap Server
            sock.sendall(json.dumps(client_info).encode('utf-8'))
            print(f"Connected to Bootstrap Server and sent info: {client_info}")

            response = sock.recv(1024).decode()
            print(f"Received response: {response}")

            if response == "authPrimary":
                self.handle_auth_primary(sock)

            elif response == "fdnPrimary":
                self.handle_fdn_primary(sock)

    def handle_auth_primary(self, sock):
        node = Node(name="authPrimaryNode", port=9001)
        threading.Thread(target=node.start_auth_primary_server).start()
        # Start authPrimary.py process
        process = subprocess.Popen(["python", "authPrimary.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   text=True)

        # Send confirmation back to Bootstrap Server
        sock.sendall(b"authPrimary setup complete")

        # Wait for list from server
        list_data = sock.recv(1024).decode()
        print(f"Received list data: {list_data}")

        file_data = sock.recv(1024).decode()
        print(f"Received file data: {file_data}")

        process.stdin.write("ACTION1" + list_data)
        process.stdin.flush()

        process.stdin.write("ACTION2" + file_data)
        process.stdin.flush()

        process.stdin.close()

    def handle_fdn_primary(self, sock):
        # node = Node(name="fdnPrimaryNode", port=9001)
        # threading.Thread(target=node.start_fdn_primary_server).start()
        # Start fdnPrimary.py process
        process = subprocess.Popen(["python", "fdnPrimary.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   text=True)

        # Send confirmation back to Bootstrap Server
        sock.sendall(b"fdnPrimary setup complete")

        # Wait for list from server
        list_data = sock.recv(1024).decode()
        print(f"Received list data: {list_data}")


        file_size_data = sock.recv(8)
        file_size = int.from_bytes(file_size_data, byteorder='big')
        print(f"Audio File size: {file_size}")

        mp3_data = b''
        mp3_data_encoded = ''
        while len(mp3_data) < file_size:
            chunk = sock.recv(4096)
            if not chunk:
                break
            mp3_data += chunk

        # Convert mp3_data to base64
        encoded = base64.b64encode(mp3_data).decode('utf-8') + "<END_OF_DATA>"

        process.stdin.write(encoded)
        # process.stdin.flush()

        process.stdin.close()

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
    bootstrap_ip = '192.168.0.119'
    client.connect_to_bootstrap(bootstrap_ip, 8000)
    # node = Node(name="authPrimaryNode", port=9001)
    # node.start_auth_primary_server()
