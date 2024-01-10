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
        self.authSub1_ip = None
        self.authSub1_port = None
        self.authSub1_numOfConnectedClients = 0
        self.authSub2_ip = None
        self.authSub2_port = None
        self.authSub2_numOfConnectedClients = 0

        self.subAuthWithLowestNumOfClients_ip = None
        self.subAuthWithLowestNumOfClients_port = None
        self.subAuthWithLowestNumOfClients_numOfConnectedClients = 0

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
        print(f"Number of authSubs: {self.numOfAuthSubs}")

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

        # Tell subAuths to start sending heartbeats
        sock.sendall(b"Start heartbeat")
        self.handle_authSub_heartbeat(sock, addr)


        # print(f"\n")
        # print(addr[0])
        # print(addr[1])
        # print(self.authSub_list[0][0])  # ip
        # print(self.authSub_list[0][1])  # port


        # threading.Thread(target=self.handle_authSub_heartbeat, args=(sock,)).start()

    def handle_authSub_heartbeat(self, sock, addr):
        while True:
            heartbeat_message = sock.recv(1024).decode()

            json_heartbeat = json.loads(heartbeat_message)

            # Get the ip and port of the authSub that sent the heartbeat
            hb_authsub_ip = json_heartbeat[0]
            hb_authsub_port = json_heartbeat[1]
            # Get the number of connected clients
            hb_numofconnectedclients = json_heartbeat[2]

            print(f"Received heartbeat message from {hb_authsub_ip}, {hb_authsub_port}: {json_heartbeat}")

            if self.subAuthWithLowestNumOfClients_ip is None:
                self.subAuthWithLowestNumOfClients_ip = hb_authsub_ip
                self.subAuthWithLowestNumOfClients_port = hb_authsub_port
                self.subAuthWithLowestNumOfClients_numOfConnectedClients = hb_numofconnectedclients
                print(f"New subAuth with lowest number of clients: {self.subAuthWithLowestNumOfClients_ip}, {self.subAuthWithLowestNumOfClients_port}, {self.subAuthWithLowestNumOfClients_numOfConnectedClients}")

            elif hb_numofconnectedclients < self.subAuthWithLowestNumOfClients_numOfConnectedClients:
                self.subAuthWithLowestNumOfClients_ip = hb_authsub_ip
                self.subAuthWithLowestNumOfClients_port = hb_authsub_port
                self.subAuthWithLowestNumOfClients_numOfConnectedClients = hb_numofconnectedclients
                print(f"New subAuth with lowest number of clients: {self.subAuthWithLowestNumOfClients_ip}, {self.subAuthWithLowestNumOfClients_port}, {self.subAuthWithLowestNumOfClients_numOfConnectedClients}")

            else:
                print("No new subAuth with lowest number of clients")


            # if hb_authsub_ip == self.authSub1_ip and hb_authsub_port == self.authSub1_port:
            #     self.authSub1_numOfConnectedClients = hb_numofconnectedclients
            #
            # elif hb_authsub_ip == self.authSub2_ip and hb_authsub_port == self.authSub2_port:
            #     self.authSub2_numOfConnectedClients = hb_numofconnectedclients
            time.sleep(5)

    def handle_client_connection(self, sock):

        # Add account functionality
        # Receive the client's username and password
        # username = sock.recv(1024).decode()
        # print(f"Received username: {username}")
        # password = sock.recv(1024).decode()
        # print(f"Received password: {password}")

        # Check if the username already exists
        # If it does, send a message to the client saying that the username already exists
        # If it doesn't, add the username and password to the file
        # Send a message to the client saying that the account was created successfully

        client_logins_file = 'clientLogins.txt'
        while True:
            # Receive the client's username and password
            username = sock.recv(1024).decode()
            print(f"Received username: {username}")
            password = sock.recv(1024).decode()
            print(f"Received password: {password}")

            # Read the existing accounts
            with open(client_logins_file, 'r') as file:
                existing_accounts = file.readlines()

            # Check if the username already exists
            account_exists = False
            for account in existing_accounts:
                stored_username, _ = account.strip().split(',')
                if username == stored_username:
                    account_exists = True
                    break

            if account_exists:
                # Inform client that username is taken
                print(f"\n** User {username} found! **\n")
                sock.sendall("User found".encode())
                break
            else:
                # Add new account and inform client of successful creation
                with open(client_logins_file, 'a') as file:
                    # Ensure the new account starts on a new line
                    if existing_accounts and not existing_accounts[-1].endswith('\n'):
                        file.write('\n')
                    file.write(f"{username},{password}\n")
                print(f"\n** Added new account: {username}, {password} **\n")
                sock.sendall("Account created successfully.".encode())
                break

        # Send the client to the authSub with the lowest number of connected clients
        client_message = sock.recv(1024).decode()
        print(f"Received message from client: {client_message}")

        if client_message == 'Need authSub address':
            authsub_ip_to_send = self.subAuthWithLowestNumOfClients_ip
            print(f"authSub_ip_to_send: {authsub_ip_to_send}")
            authsub_port_to_send = self.subAuthWithLowestNumOfClients_port
            print(f"authSub_port_to_send: {authsub_port_to_send}")
            #
            # if self.authSub1_numOfConnectedClients <= self.authSub2_numOfConnectedClients:
            #     print(f"authSub1 has less clients than authSub2")
            #     authsub_ip_to_send = self.authSub1_ip
            #     authsub_port_to_send = self.authSub1_port
            # elif self.authSub1_numOfConnectedClients > self.authSub2_numOfConnectedClients:
            #     print(f"authSub2 has less clients than authSub1")
            #     authsub_ip_to_send = self.authSub2_ip
            #     authsub_port_to_send = self.authSub2_port

            # Send the ip and port to the authSub
            sock.sendall(authsub_ip_to_send.encode())
            print(f"Sent authSub ip: {authsub_ip_to_send}")
            sock.sendall(authsub_port_to_send.to_bytes(8, byteorder='big'))
            print(f"Sent authSub port: {authsub_port_to_send}")


if __name__ == '__main__':
    new_AuthPrimary = AuthPrimary(name="authPrimary")

    # Connect the client to the Bootstrap Server
    bootstrap_ip = open('bootstrap_ip.txt', 'r').read().strip()
    new_AuthPrimary.connect_to_bootstrap(bootstrap_ip, 50000)
