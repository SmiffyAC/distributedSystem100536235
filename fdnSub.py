import socket
import json
import subprocess
import base64
import threading

import os
import sys
import time


class FdnSub:
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

        self.number_of_files = None
        self.json_audio_file_list = None


        print(f"FdnSub set up on: {self.host}, Node Port: {self.port}")

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

            self.number_of_files = int.from_bytes(sock.recv(8), byteorder='big')
            print(f"Expected number of audio files: {self.number_of_files}")

            audio_file_list = sock.recv(1024).decode()
            print(f"Received audio file list: {audio_file_list}")
            self.json_audio_file_list = json.loads(audio_file_list)
            print(f"JSON audio file list: {self.json_audio_file_list}")

            file = 0

            audio_file_size_list = []
            audio_file_data_list = []

            while file < self.number_of_files:
                audio_file_size_data = sock.recv(8)
                audio_file_size = int.from_bytes(audio_file_size_data, byteorder='big')
                print(f"Audio File size: {audio_file_size}")

                mp3_data = b''
                mp3_data_encoded = ''
                while len(mp3_data) < audio_file_size:
                    chunk = sock.recv(min(4096, audio_file_size - len(mp3_data)))
                    if not chunk:
                        break
                    mp3_data += chunk

                audio_file_size_list.append(audio_file_size)
                print(audio_file_size_list)
                audio_file_data_list.append(mp3_data)
                print(f"File {file} received")
                file += 1

            sock.sendall(b"All files Received")

            # HANDLE THE DATA IT WILL RECEIVE PRIMARY FDN ADDRESS FROM THE BOOTSTRAP SERVER
            if sock.recv(1024).decode() == "Ready to provide fdnPrimary address":
                sock.sendall(b"fdnPrimary address")
                # Wait for fdn address from server
                fdn_primary_ip = sock.recv(1024).decode()
                print(f"Received fdnPrimary address: {fdn_primary_ip}")

                fdn_primary_port = int.from_bytes(sock.recv(8), byteorder='big')
                print(f"Received fdnPrimary port: {fdn_primary_port}")

            # threading.Thread(target=self.connect_to_authPrimary).start()
            # self.connect_to_authPrimary(auth_primary_ip, auth_primary_port)
            threading.Thread(target=self.connect_to_fdnPrimary, args=(fdn_primary_ip, fdn_primary_port)).start()

    def connect_to_fdnPrimary(self, fdn_primary_ip, fdn_primary_port):
        print(f"\nWaiting for fdnPrimary to be ready at {fdn_primary_ip}:{fdn_primary_port}")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

            s.connect((fdn_primary_ip, fdn_primary_port))

            s.sendall(b"fdnSub")

            print(f"Connected to Fdn Primary at {fdn_primary_ip}:{fdn_primary_port}")

            fdnPrimary_message = s.recv(1024).decode()
            print(f"Received message from Fdn Primary: {fdnPrimary_message}")

            # Provide the authPrimary with the address and port of the authSub
            if fdnPrimary_message == "Address and Port":
                s.sendall(self.host.encode())
                print(f"Sent FdnSub address: {self.host}")
                s.sendall(self.port.to_bytes(8, byteorder='big'))
                print(f"Sent FdnSub port: {self.port}")

            fdnPrimary_message_2 = s.recv(1024).decode()

            if fdnPrimary_message_2 == "Start heartbeat":
                self.send_heartbeat_to_fdnPrimary(s)

                # threading.Thread(target=self.send_heartbeat_to_authPrimary, args=(s,)).start()
                # self.handle_client_connection()
                # threading.Thread(target=self.handle_client_connection).start()

    def send_heartbeat_to_fdnPrimary(self, s):
        print(f"IN SEND_HEARTBEAT_TO_FDNPRIMARY - Sending heartbeat to Fdn Primary")
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
            # print(f"Sent heartbeat to Fdn Primary")
            time.sleep(10)

    def handle_client_connection(self):
        print(f"IN HANDLE_CLIENT_CONNECTION - Inside thread for handle_client_connection")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((self.host, self.port))
            sock.listen()
            print(f"fdnSub now listening for clients on {self.host}:{self.port}")

            while True:
                node, addr = sock.accept()
                print(f"Accepted connection from client with info: {addr}")

                client_message = node.recv(1024).decode()
                print(f"Received message from client: {client_message}")

                if client_message == 'audio file':
                    time_stamp = str(time.time())
                    token = str(self.host) + "|" + str(self.port) + "|" + time_stamp
                    print(f"Token: {token}")
                    node.sendall(token.encode())
                    print(f"Sent token: {token}")
                    # input("Press Enter to exit... - AFTER SENDING TOKEN")


if __name__ == '__main__':
    new_FdnSub = FdnSub(name="fdnSub")

    # Connect the client to the Bootstrap Server
    bootstrap_ip = open('bootstrap_ip.txt', 'r').read().strip()
    new_FdnSub.connect_to_bootstrap(bootstrap_ip, 50000)
