import socket
import json
import subprocess
import base64
import threading

import os
import sys
import time


class AuthPrimary:
    def __init__(self, name):
        # Initialize the client with a name, host, and port
        node_name = socket.gethostname()
        hostname, aliases, ip_addresses = socket.gethostbyname_ex(node_name)

        # Filter for IP addresses that start with '10'
        ip_address_10 = next((ip for ip in ip_addresses if ip.startswith('10')), None)
        self.name = name
        self.host = ip_address_10
        self.port = self.find_open_port()
        self.authSub_ip = None
        self.authSub_port = None
        self.authSub_list = []
        self.authSub_file = None
        self.numOfAuthSubs = 0
        print(f"AuthPrimary set up on: {self.host}, Node Port: {self.port}")

        threading.Thread(target=self.accept_client_connection).start()

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
            if sock.recv(1024).decode() == "Address and Port":
                sock.sendall(self.host.encode())
                print(f"Sent authPrimary ip: {self.host}")
                sock.sendall(self.port.to_bytes(8, byteorder='big'))
                print(f"Sent authPrimary port: {self.port}")

            # Wait for list from server
            # self.authSub_list.append(sock.recv(1024).decode())
            # print(f"Received list data: {self.authSub_list}")
            # received_list_data = sock.recv(1024).decode()
            # print(f"\nReceived list data: {received_list_data}")
            # auth_sub_info = json.loads(received_list_data)
            # self.authSub_list.append(auth_sub_info)
            # print(f"\nReceived list data: {self.authSub_list}")

            self.authSub_file = sock.recv(1024).decode()
            print(f"Received file data: {self.authSub_file}")

            # threading.Thread(target=self.accept_client_connection).start()

            # self.do_somthing_else()

    # def do_somthing_else(self):
    #     # Keep the program running - wait for user input
    #     input("Press Enter to exit...")

    def accept_client_connection(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((self.host, self.port))
            sock.listen()
            print(f"authPrimary now listening on {self.host}:{self.port}")

            while True:
                node, addr = sock.accept()
                print(f"\nAccepted connection from {addr}")

                connection_message = node.recv(1024).decode()

                if connection_message == 'authSub':
                    threading.Thread(target=self.handle_authSub_connection, args=(node, addr)).start()

                elif connection_message == 'client':
                    threading.Thread(target=self.handle_client_connection, args=(node,)).start()

    def handle_authSub_connection(self, sock, addr):

        print(f"\nA new authSub has connected from: {addr}")
        self.numOfAuthSubs += 1

        print("Waiting for second authSub to connect")
        while True:
            try:
                if self.numOfAuthSubs == 2:
                    # Receive the authSub address and port
                    sock.sendall(b"Address and Port")
                    print(f"Asked subAuth for address and port")

                    self.authSub_ip = sock.recv(1024).decode()
                    print(f"Received authSub address: {self.authSub_ip}")
                    self.authSub_port = int.from_bytes(sock.recv(8), byteorder='big')
                    print(f"Received authSub port: {self.authSub_port}")
                    break
            except:
                pass

        # print(f"\n")
        # print(addr[0])
        # print(addr[1])
        # print(self.authSub_list[0][0])  # ip
        # print(self.authSub_list[0][1])  # port

        self.handle_authSub_hearbeat(sock, addr)
        # threading.Thread(target=self.handle_authSub_hearbeat, args=(sock,)).start()

    def handle_authSub_hearbeat(self, sock, addr):
        while True:
            heartbeat_message = sock.recv(1024).decode()

            json_heartbeat = json.loads(heartbeat_message)

            # Get the ip and port of the authSub that sent the heartbeat
            authSub_ip = json_heartbeat[0]
            authSub_port = json_heartbeat[1]
            # Get the number of connected clients
            numOfConnectedClients = json_heartbeat[2]

            print(f"Received heartbeat message: {json_heartbeat}")

            time.sleep(5)

    def handle_client_connection(self, sock):

        client_message = sock.recv(1024).decode()
        print(f"Received message from client: {client_message}")

        if client_message == 'Need authSub address':
            # LATER THE BELOW WILL BE PUT INTO A LOAD BALANCER

            # Send the ip and port to the authSub
            sock.sendall(self.authSub_ip.encode())
            print(f"Sent authSub ip: {self.authSub_ip}")
            sock.sendall(self.authSub_port.to_bytes(8, byteorder='big'))
            print(f"Sent authSub port: {self.authSub_port}")


if __name__ == '__main__':
    new_AuthPrimary = AuthPrimary(name="authPrimary")

    # Connect the client to the Bootstrap Server
    bootstrap_ip = open('bootstrap_ip.txt', 'r').read().strip()
    new_AuthPrimary.connect_to_bootstrap(bootstrap_ip, 50000)
