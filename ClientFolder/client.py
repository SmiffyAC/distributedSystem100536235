import socket
import json
import subprocess
from playsound import playsound
import pygame
import base64


class Client:
    def __init__(self, name, port=9000):
        # Initialize the client with a name, host, and port
        client_name = socket.gethostname()
        client_ip = socket.gethostbyname(client_name)
        self.name = name
        self.host = client_ip
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

            if response == 'Welcome Client':
                self.handle_auth(sock)

    def handle_auth(self, sock):
        sock.sendall(b"authPrimary address")

        # Wait for auth address from server
        auth_primary_ip = sock.recv(1024).decode()
        print(f"Received auth address: {auth_primary_ip}")

        self.connect_to_auth(auth_primary_ip)

    def connect_to_auth(self, auth_primary_ip):
        # with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        #     sock.connect((auth_ip, 9000))
        #     # Prepare the client information as JSON
        #     client_info = {"name": self.name, "ip": self.host, "port": self.port}
        #     # Send the client information to the Bootstrap Server
        #     sock.sendall(json.dumps(client_info).encode('utf-8'))
        #     print(f"Connected to Auth Server and sent info: {client_info}")
        #
        #     response = sock.recv(1024).decode()
        #     print(f"Received response: {response}")
        #
        #     if response == 'Welcome Client':
        #         self.handle_auth(sock)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

            # MAKE SURE IT IS USING THE ADDRESS THAT IS PASSED TO IT FROM THE BOOTSTRAP SERVER

            s.connect((auth_primary_ip, 9001))
            print(f"Connected to Auth Primary at {auth_primary_ip}:{9001}")
            # Send data or perform actions as needed
            s.sendall(b"token")
            authPrimary_reponse = s.recv(1024).decode()
            print("AuthPrimary:" + authPrimary_reponse)


if __name__ == '__main__':
    # Create a client instance with a unique name
    client = Client(name="client")
    # Connect the client to the Bootstrap Server
    # bootstrap_ip = '192.168.0.119'
    # bootstrap_ip = '172.26.61.101'  # IP ADDRESS AT LIBRARY
    bootstrap_ip = '192.168.56.1'  # IP ADDRESS AT MS
    client.connect_to_bootstrap(bootstrap_ip, 50000)
