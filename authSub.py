import socket
import json
import subprocess
import base64
import threading

import os
import sys
import time


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
        self.tokenSet = {}
        self.numOfConnectedClients = 0
        print(f"AuthSub set up on: {self.host}, Node Port: {self.port}")

        # COMMENTED OUT FOR TESTING
        # print(f"IN INIT - Starting thread for handle_client_connection")
        threading.Thread(target=self.handle_client_connection).start()

    def find_open_port(self):
        # Iterate through the port range to find the first open port
        port_range = (50001, 50010)
        for port in range(port_range[0], port_range[1]):
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
            print(f"\nClient info TO SEND: {client_info}")
            # Send the client information to the Bootstrap Server
            sock.sendall(json.dumps(client_info).encode('utf-8'))
            print(f"Connected to Bootstrap Server and sent info: {client_info}")

            # HANDLE THE DATA IT WILL RECEIVE PRIMARY AUTH ADDRESS FROM THE BOOTSTRAP SERVER
            if sock.recv(1024).decode() == "Ready to provide authPrimary address":

                sock.sendall(b"authPrimary address")
                # Wait for auth address from server
                auth_primary_ip = sock.recv(1024).decode()
                print(f"Received authPrimary address: {auth_primary_ip}")

                auth_primary_port = int.from_bytes(sock.recv(8), byteorder='big')
                print(f"Received authPrimary port: {auth_primary_port}")

            # threading.Thread(target=self.connect_to_authPrimary).start()
            # self.connect_to_authPrimary(auth_primary_ip, auth_primary_port)
            threading.Thread(target=self.connect_to_authPrimary, args=(auth_primary_ip, auth_primary_port)).start()


    def connect_to_authPrimary(self, auth_primary_ip, auth_primary_port):
        print(f"\nWaiting for authPrimary to be ready at {auth_primary_ip}:{auth_primary_port}")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

            s.connect((auth_primary_ip, auth_primary_port))

            s.sendall(b"authSub")

            print(f"Connected to Auth Primary at {auth_primary_ip}:{auth_primary_port}")

            authPrimary_message = s.recv(1024).decode()
            print(f"Received message from Auth Primary: {authPrimary_message}")

            # Provide the authPrimary with the address and port of the authSub
            if authPrimary_message == "Address and Port":
                s.sendall(self.host.encode())
                print(f"Sent AuthSub address: {self.host}")
                s.sendall(self.port.to_bytes(8, byteorder='big'))
                print(f"Sent AuthSub port: {self.port}")

            authPrimary_message_2 = s.recv(1024).decode()

            if authPrimary_message_2 == "Start heartbeat":
                self.send_heartbeat_to_authPrimary(s)

                # threading.Thread(target=self.send_heartbeat_to_authPrimary, args=(s,)).start()
                # self.handle_client_connection()
                # threading.Thread(target=self.handle_client_connection).start()

    def send_heartbeat_to_authPrimary(self, s):
        print(f"IN SEND_HEARTBEAT_TO_AUTHPRIMARY - Sending heartbeat to Auth Primary")
        time.sleep(5)
        while True:
            heartbeatList = []
            heartbeatList.append(self.host)
            heartbeatList.append(self.port)
            heartbeatList.append(self.numOfConnectedClients)

            heartbeat = json.dumps(heartbeatList)
            print(f"Heartbeat Sent: {heartbeat}")
            s.sendall(heartbeat.encode())
            # s.sendall(b"heartbeat")
            # print(f"Sent heartbeat to Auth Primary")
            time.sleep(10)

    def handle_client_connection(self):
        print(f"IN HANDLE_CLIENT_CONNECTION - Inside thread for handle_client_connection")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((self.host, self.port))
            sock.listen()
            print(f"authSub now listening for clients on {self.host}:{self.port}")

            while True:
                node, addr = sock.accept()
                print(f"Accepted connection from client with info: {addr}")

                client_message = node.recv(1024).decode()
                print(f"Received message from client: {client_message}")

                if client_message == 'token':
                    time_stamp = str(time.time())
                    token = str(self.host) + "|" + str(self.port) + "|" + time_stamp
                    print(f"Token: {token}")
                    node.sendall(token.encode())
                    print(f"Sent token: {token}")
                    # input("Press Enter to exit... - AFTER SENDING TOKEN")


if __name__ == '__main__':
    new_AuthSub = AuthSub(name="authSub")

    # Connect the client to the Bootstrap Server
    bootstrap_ip = open('bootstrap_ip.txt', 'r').read().strip()
    new_AuthSub.connect_to_bootstrap(bootstrap_ip, 50000)
