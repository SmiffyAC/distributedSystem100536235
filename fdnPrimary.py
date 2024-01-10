import socket
import json
import subprocess
import base64
import threading

import os
import sys
import time


class FdnPrimary:
    def __init__(self, name):
        # Initialize the client with a name, host, and port
        node_name = socket.gethostname()
        hostname, aliases, ip_addresses = socket.gethostbyname_ex(node_name)

        # Filter for IP addresses that start with '10'
        ip_address_10 = next((ip for ip in ip_addresses if ip.startswith('10')), None)
        self.name = name
        self.host = ip_address_10
        self.port = self.find_open_port()
        self.fdnSub1_ip = None
        self.fdnSub1_port = None
        self.fdnSub1_numOfConnectedClients = 0
        self.fdnSub2_ip = None
        self.fdnSub2_port = None
        self.fdnSub2_numOfConnectedClients = 0

        self.subFdnWithLowestNumOfClients_ip = None
        self.subFdnWithLowestNumOfClients_port = None
        self.subFdnWithLowestNumOfClients_numOfConnectedClients = 100

        self.fdnSub_list = []
        self.fdnSub_file = []
        self.numOfFdnSubs = 0
        print(f"FdnPrimary set up on: {self.host}, Node Port: {self.port}")

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
        print(f"FdnPrimary connecting to Bootstrap Server at {bootstrap_host}:{bootstrap_port}")
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
                print(f"Sent fdnPrimary ip: {self.host}")
                sock.sendall(self.port.to_bytes(8, byteorder='big'))
                print(f"Sent fdnPrimary port: {self.port}")

            # number_of_files = int.from_bytes(sock.recv(8), byteorder='big')
            # print(f"Expected number of audio files: {number_of_files}")
            #
            # file = 0
            #
            # audio_file_size_list = []
            # audio_file_data_list = []
            #
            # while file < number_of_files:
            #     audio_file_size_data = sock.recv(8)
            #     audio_file_size = int.from_bytes(audio_file_size_data, byteorder='big')
            #     print(f"Audio File size: {audio_file_size}")
            #
            #     mp3_data = b''
            #     mp3_data_encoded = ''
            #     while len(mp3_data) < audio_file_size:
            #         chunk = sock.recv(min(4096, audio_file_size - len(mp3_data)))
            #         if not chunk:
            #             break
            #         mp3_data += chunk
            #
            #     audio_file_size_list.append(audio_file_size)
            #     print(audio_file_size_list)
            #     audio_file_data_list.append(mp3_data)
            #     print(f"File {file} received")
            #     file += 1

            # threading.Thread(target=self.accept_client_connection).start()

    def accept_client_connection(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((self.host, self.port))
            sock.listen()
            print(f"fdnPrimary now listening on {self.host}:{self.port}")

            while True:
                node, addr = sock.accept()
                print(f"\nAccepted connection from {addr}")

                connection_message = node.recv(1024).decode()

                if connection_message == 'fdnSub':
                    threading.Thread(target=self.handle_fdnSub_connection, args=(node, addr)).start()

                elif connection_message == 'client':
                    threading.Thread(target=self.handle_client_connection, args=(node,)).start()

    def handle_fdnSub_connection(self, sock, addr):

        print(f"\nA new fdnSub has connected from: {addr}")
        self.numOfFdnSubs += 1
        print(f"Number of fdnSubs: {self.numOfFdnSubs}")

        print("Waiting for second fdnSub to connect")

        while True:
            try:
                if self.numOfFdnSubs == 2:
                    # Receive the fdnSub address and port
                    sock.sendall(b"Address and Port")
                    print(f"Asked subFdn for address and port")

                    self.fdnSub_ip = sock.recv(1024).decode()
                    print(f"Received fdnSub address: {self.fdnSub_ip}")
                    self.fdnSub_port = int.from_bytes(sock.recv(8), byteorder='big')
                    print(f"Received fdnSub port: {self.fdnSub_port}")
                    break
            except:
                pass

        # Tell subFdns to start sending heartbeats
        sock.sendall(b"Start heartbeat")
        self.handle_fdnSub_heartbeat(sock, addr)

    def handle_fdnSub_heartbeat(self, sock, addr):
        while True:
            heartbeat_message = sock.recv(1024).decode()

            json_heartbeat = json.loads(heartbeat_message)

            # Get the ip and port of the fdnSub that sent the heartbeat
            hb_fdnsub_ip = json_heartbeat[0]
            hb_fdnsub_port = json_heartbeat[1]
            # Get the number of connected clients
            hb_numofconnectedclients = int(json_heartbeat[2])

            print(f"\nhb_fdnsub_ip: {hb_fdnsub_ip}")
            print(f"hb_fdnsub_port: {hb_fdnsub_port}")
            print(f"hb_numofconnectedclients: {hb_numofconnectedclients}\n")
            print(f"subFdnWithLowestNumOfClients_numOfConnectedClients: {self.subFdnWithLowestNumOfClients_numOfConnectedClients}")

            print(f"Received heartbeat message from {hb_fdnsub_ip}, {hb_fdnsub_port}: {json_heartbeat}")

            if self.subFdnWithLowestNumOfClients_ip is None:
                self.subFdnWithLowestNumOfClients_ip = hb_fdnsub_ip
                self.subFdnWithLowestNumOfClients_port = hb_fdnsub_port
                self.subFdnWithLowestNumOfClients_numOfConnectedClients = hb_numofconnectedclients
                print(f"New subFdn with lowest number of clients: {self.subFdnWithLowestNumOfClients_ip}, {self.subFdnWithLowestNumOfClients_port}, {self.subFdnWithLowestNumOfClients_numOfConnectedClients}")

            elif hb_fdnsub_ip == self.subFdnWithLowestNumOfClients_ip and hb_fdnsub_port == self.subFdnWithLowestNumOfClients_port:
                self.subFdnWithLowestNumOfClients_ip = hb_fdnsub_ip
                self.subFdnWithLowestNumOfClients_port = hb_fdnsub_port
                self.subFdnWithLowestNumOfClients_numOfConnectedClients = hb_numofconnectedclients
                print(f"Updated values for subFdn with lowest number of clients: {self.subFdnWithLowestNumOfClients_ip}, {self.subFdnWithLowestNumOfClients_port}, {self.subFdnWithLowestNumOfClients_numOfConnectedClients}")

            elif hb_numofconnectedclients < self.subFdnWithLowestNumOfClients_numOfConnectedClients:
                self.subFdnWithLowestNumOfClients_ip = hb_fdnsub_ip
                self.subFdnWithLowestNumOfClients_port = hb_fdnsub_port
                self.subFdnWithLowestNumOfClients_numOfConnectedClients = hb_numofconnectedclients
                print(f"\n** New subFdn with lowest number of clients: {self.subFdnWithLowestNumOfClients_ip}, {self.subFdnWithLowestNumOfClients_port}, {self.subFdnWithLowestNumOfClients_numOfConnectedClients} **\n")

            else:
                print("No new subFdn with lowest number of clients")
                print(f"Current subFdn with lowest number of clients: {self.subFdnWithLowestNumOfClients_ip}, {self.subFdnWithLowestNumOfClients_port}, {self.subFdnWithLowestNumOfClients_numOfConnectedClients}")

            # time.sleep(5)

    def handle_client_connection(self, sock):
        try:
            client_message = sock.recv(1024).decode()
            print(f"Received message from client: {client_message}")

            if client_message == "Need fdnSub address":
                fdnsub_ip_to_send = self.subFdnWithLowestNumOfClients_ip
                print(f"fdnSub_ip_to_send: {fdnsub_ip_to_send}")
                fdnsub_port_to_send = self.subFdnWithLowestNumOfClients_port
                print(f"fdnSub_port_to_send: {fdnsub_port_to_send}")

                # Send the ip and port to the fdnSub
                sock.sendall(fdnsub_ip_to_send.encode())
                print(f"Sent fdnSub ip: {fdnsub_ip_to_send}")
                sock.sendall(fdnsub_port_to_send.to_bytes(8, byteorder='big'))
                print(f"Sent fdnSub port: {fdnsub_port_to_send}")

        except ConnectionResetError:
            print("Client disconnected unexpectedly.")
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            sock.close()
            print("Connection to client closed.")


if __name__ == '__main__':
    new_FdnPrimary = FdnPrimary(name="fdnPrimary")

    # Connect the client to the Bootstrap Server
    bootstrap_ip = open('bootstrap_ip.txt', 'r').read().strip()
    new_FdnPrimary.connect_to_bootstrap(bootstrap_ip, 50000)
