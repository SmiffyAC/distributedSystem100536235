import socket
import json
import subprocess
import base64
import threading

import os
import sys


# from netifaces import interfaces, ifaddresses, AF_INET


class Node:
    def __init__(self, name):
        # Initialize the client with a name, host, and port
        node_name = socket.gethostname()
        node_ip = socket.gethostbyname(node_name)
        self.name = name
        self.host = node_ip
        # self.port = self.find_open_port()

    # def find_open_port(self):
    #     # Iterate through the port range to find the first open port
    #     port_range = (50001, 50010)
    #     for port in range(port_range[0], port_range[1] + 1):
    #         with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    #             if sock.connect_ex((self.host, port)) != 0:
    #                 # Port is open, use this one
    #                 return port
    #     raise Exception("No open ports available in the specified range.")

    def connect_to_bootstrap(self, bootstrap_host, bootstrap_port):

        # Connect to the Bootstrap Server
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((bootstrap_host, bootstrap_port))
            # Prepare the client information as JSON
            client_info = {"name": self.name, "ip": self.host}
            # Send the client information to the Bootstrap Server
            sock.sendall(json.dumps(client_info).encode('utf-8'))
            print(f"Connected to Bootstrap Server and sent info: {client_info}")

            while True:

                response = sock.recv(1024).decode()
                print(f"Received response: {response}")

                if response == "authPrimary":
                    self.handle_authPrimary_creation()

                elif response == "fdnPrimary":
                    self.handle_fdnPrimary_creation()

                # elif response == "sub":
                #     self.handle_sub_creation()

                elif response == "subAuth":
                    self.handle_subAuth_creation()

                elif response == "subFdn":
                    self.handle_subFdn_creation()

    def handle_authPrimary_creation(self):

        print(f"Starting authPrimary.py")

        pid = subprocess.Popen([sys.executable, "authPrimary.py"],
                               creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NEW_CONSOLE).pid

    def handle_fdnPrimary_creation(self):

        print(f"Starting fdnPrimary.py")

        pid = subprocess.Popen([sys.executable, "fdnPrimary.py"],
                               creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NEW_CONSOLE).pid

    # def handle_sub_creation(self):
    #     # Needs to start listening for connections from either the fdnPrimary or authPrimary
    #     pass

    def handle_subAuth_creation(self):

        print(f"Starting authSub.py")

        pid = subprocess.Popen([sys.executable, "authSub.py"],
                               creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NEW_CONSOLE).pid

    def handle_subFdn_creation(self):

        print(f"Starting fdnSub.py")

        pid = subprocess.Popen([sys.executable, "fdnSub.py"],
                               creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NEW_CONSOLE).pid


if __name__ == '__main__':
    # Create a client instance with a unique name
    new_node = Node(name="node")
    # Connect the client to the Bootstrap Server
    bootstrap_ip = open('bootstrap_ip.txt', 'r').read().strip()
    new_node.connect_to_bootstrap(bootstrap_ip, 50000)
