import socket
import json
import subprocess
import base64
import threading

import os
import sys


class AuthSub:
    def __init__(self, name):
        # Initialize the client with a name, host, and port
        node_name = socket.gethostname()
        hostname, aliases, ip_addresses = socket.gethostbyname_ex(node_name)

        # Filter for IP addresses that start with '10'
        ip_address_10 = next((ip for ip in ip_addresses if ip.startswith('10')), None)
        self.name = name
        self.host = ip_address_10
        self.port = self.find_open_port()
        print(f"AuthSub set up on: {self.host}, Node Port: {self.port}")

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
        print(f"AuthSub connecting to Bootstrap Server at {bootstrap_host}:{bootstrap_port}")
        # Connect to the Bootstrap Server
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((bootstrap_host, bootstrap_port))
            # Prepare the client information as JSON
            client_info = {"name": self.name, "ip": self.host, "port": self.port}
            # Send the client information to the Bootstrap Server
            sock.sendall(json.dumps(client_info).encode('utf-8'))
            print(f"Connected to Bootstrap Server and sent info: {client_info}")

            # HANDLE THE DATA IT WILL RECEIVE PRIMARY AUTH ADDRESS FROM THE BOOTSTRAP SERVER

            sock.sendall(b"authPrimary address")

            # Wait for auth address from server
            auth_primary_ip = sock.recv(1024).decode()
            print(f"Received auth address: {auth_primary_ip}")

            auth_primary_port = int.from_bytes(sock.recv(8), byteorder='big')
            print(f"Received auth port: {auth_primary_port}")

            # threading.Thread(target=self.connect_to_authPrimary).start()
            self.connect_to_authPrimary(auth_primary_ip, auth_primary_port)


    def connect_to_authPrimary(self, auth_primary_ip, auth_primary_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

            s.connect((auth_primary_ip, auth_primary_port))

            while True:

                s.sendall(b"authSub")

                print(f"Connected to Auth Primary at {auth_primary_ip}:{auth_primary_port}")

                input("Press Enter to exit...")




if __name__ == '__main__':
    new_AuthSub = AuthSub(name="authSub")

    # Connect the client to the Bootstrap Server
    bootstrap_ip = open('bootstrap_ip.txt', 'r').read().strip()
    new_AuthSub.connect_to_bootstrap(bootstrap_ip, 50000)
