import socket
import json
import subprocess
# from playsound import playsound
# import pygame
import base64


class Client:
    def __init__(self, name):
        # Initialize the client with a name, host, and port
        node_name = socket.gethostname()
        hostname, aliases, ip_addresses = socket.gethostbyname_ex(node_name)

        # Filter for IP addresses that start with '10'
        ip_address_10 = next((ip for ip in ip_addresses if ip.startswith('10')), None)
        self.name = name
        self.host = ip_address_10
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

            response = sock.recv(1024).decode()
            print(f"Received response: {response}")

            if response == 'Welcome client':
                self.handle_auth(sock)

    def handle_auth(self, sock):
        print("Handling auth")
        sock.sendall(b"authPrimary address")

        # Wait for auth address from server
        auth_primary_ip = sock.recv(1024).decode()
        print(f"Received auth address: {auth_primary_ip}")

        auth_primary_port = int.from_bytes(sock.recv(8), byteorder='big')
        print(f"Received auth port: {auth_primary_port}")

        self.connect_to_auth(auth_primary_ip, auth_primary_port)

    def connect_to_auth(self, auth_primary_ip, auth_primary_port):
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
            s.connect((auth_primary_ip, auth_primary_port))

            # MAKE SURE IT IS USING THE ADDRESS THAT IS PASSED TO IT FROM THE BOOTSTRAP SERVER

            while True:
                print(f"Connected to Auth Primary at {auth_primary_ip}:{auth_primary_port}")
                # Send data or perform actions as needed
                s.sendall(b"token")

                authSub_ip = s.recv(1024).decode()
                print("AuthPrimary:" + authSub_ip)

                input("Press Enter to exit...")


if __name__ == '__main__':
    # Create a client instance with a unique name
    client = Client(name="client")
    # Connect the client to the Bootstrap Server
    bootstrap_ip = open('bootstrap_ip.txt', 'r').read().strip()
    client.connect_to_bootstrap(bootstrap_ip, 50000)
