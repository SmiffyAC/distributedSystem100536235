import socket
import json
import subprocess
import base64
import threading

import os
import sys


class AuthPrimary:
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
        print(f"AuthPrimary connecting to Bootstrap Server at {bootstrap_host}:{bootstrap_port}")
        # Connect to the Bootstrap Server
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((bootstrap_host, bootstrap_port))
            # Prepare the client information as JSON
            client_info = {"name": self.name, "ip": self.host, "port": self.port}
            # Send the client information to the Bootstrap Server
            sock.sendall(json.dumps(client_info).encode('utf-8'))
            print(f"Connected to Bootstrap Server and sent info: {client_info}")

            # HANDLE THE DATA IT WILL RECEIVE FROM THE BOOTSTRAP SERVER

            # Wait for list from server
            client_list_data = sock.recv(1024).decode()
            print(f"Received list data: {client_list_data}")

            client_file_data = sock.recv(1024).decode()
            print(f"Received file data: {client_file_data}")

            threading.Thread(target=self.handle_client_connection).start()

            # self.do_somthing_else()



    # def do_somthing_else(self):
    #     # Keep the program running - wait for user input
    #     input("Press Enter to exit...")

    def handle_client_connection(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((self.host, self.port))
            sock.listen()
            print(f"Now listening on {self.host}:{self.port}")

            while True:
                node, addr = sock.accept()
                print(f"Accepted connection from {addr}")

                message = sock.recv(1024).decode()
                print(f"Received message: {message}")




if __name__ == '__main__':
    new_AuthPrimary = AuthPrimary(name="authPrimary")

    # Connect the client to the Bootstrap Server
    bootstrap_ip = open('bootstrap_ip.txt', 'r').read().strip()
    new_AuthPrimary.connect_to_bootstrap(bootstrap_ip, 50000)
