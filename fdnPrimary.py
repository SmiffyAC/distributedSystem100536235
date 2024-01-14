import socket
import json
import threading
import argparse
import os
import time
import random
import hashlib


class FdnPrimary:
    def __init__(self, name):
        # Initialize the client with a name, host, and port
        self.fdnSub_port = None
        self.fdnSub_ip = None
        node_name = socket.gethostname()
        hostname, aliases, ip_addresses = socket.gethostbyname_ex(node_name)

        # Filter for IP addresses that start with 10
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

        self.control_node_ips = []  # List to store the control node IPs
        self.control_node_ports = []  # List to store the control node ports

        self.number_of_files = None
        self.audio_file_list = []
        self.json_audio_file_list = []

        self.audio_file_size_list = []
        self.audio_file_data_list = []
        self.md5_hash_list = []

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

            if sock.recv(1024).decode() == "Ready to provide controlNode list":
                # Receive the control node ips
                self.control_node_ips = json.loads(sock.recv(1024).decode())
                print(f"Received controlNode ips: {self.control_node_ips}")
                self.control_node_ports = json.loads(sock.recv(1024).decode())
                print(f"Received controlNode ports: {self.control_node_ports}")

                # RECEIVED THE AUDIO FILES

                self.number_of_files = int.from_bytes(sock.recv(8), byteorder='big')
                print(f"Expected number of audio files: {self.number_of_files}")

                audio_file_list = sock.recv(1024).decode()
                self.audio_file_list = audio_file_list
                self.json_audio_file_list = json.loads(audio_file_list)
                print(f"From Bootstrap: Audio File List = {self.json_audio_file_list}")

                sock.sendall(b"Ready to receive audio files")
                print(f"Sent ready to receive audio files message")

                file = 0

                while file < self.number_of_files:
                    audio_file_size_data = sock.recv(8)
                    audio_file_size = int.from_bytes(audio_file_size_data, byteorder='big')
                    print(f"Audio File size: {audio_file_size}")

                    mp3_data = b''
                    while len(mp3_data) < audio_file_size:
                        chunk = sock.recv(min(4096, audio_file_size - len(mp3_data)))
                        if not chunk:
                            break
                        mp3_data += chunk

                    self.audio_file_size_list.append(audio_file_size)
                    print(self.audio_file_size_list)
                    self.audio_file_data_list.append(mp3_data)
                    md5_hash = sock.recv(1024)
                    print(f"From Bootstrap: Provided MD5 Hash = {md5_hash}")
                    print(md5_hash)
                    self.md5_hash_list.append(md5_hash)
                    print(f"File {file + 1} received\n")
                    sock.sendall(b"File received")
                    file += 1

                sock.sendall(b"All files Received")

                # Generate the fdnSubs
                self.generate_fdn_subs()

    def generate_fdn_subs(self):
        print(f"\n** Generating FdnSubs **")
        num_generated = 0
        while num_generated < 2:
            random_control_node_index = random.randint(0, len(self.control_node_ips) - 1)
            control_node_ip = self.control_node_ips[random_control_node_index]
            print(f"random_control_node_ip: {control_node_ip}")
            control_node_port = self.control_node_ports[random_control_node_index]
            print(f"random_control_node_port: {control_node_port}")

            # Create the fdnSub
            threading.Thread(target=self.connect_to_control_node, args=(control_node_ip, control_node_port)).start()
            num_generated += 1
            time.sleep(1)

    def connect_to_control_node(self, control_node_ip, control_node_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((control_node_ip, control_node_port))

            sock.send(b"fdnSub")

            if sock.recv(1024).decode() == "Address and Port":
                sock.sendall(self.host.encode())
                print(f"Sent FdnPrimary address: {self.host}")
                sock.sendall(self.port.to_bytes(8, byteorder='big'))
                print(f"Sent FdnPrimary port: {self.port}")

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
                    time.sleep(0.5)
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

                    self.fdnSub_ip = sock.recv(1024).decode()
                    print(f"Received fdnSub address: {self.fdnSub_ip}")
                    self.fdnSub_port = int.from_bytes(sock.recv(8), byteorder='big')
                    print(f"Received fdnSub port: {self.fdnSub_port}")

                    # Get list of all files in the 'audio_files' folder
                    all_files = os.listdir('audio_files/using')

                    # Filter out only audio files, assuming .mp3 extension
                    audio_file_paths = [file for file in all_files if file.endswith('.mp3')]

                    print(f"Audio file paths: {audio_file_paths}")

                    # Send the number of files to expect
                    number_of_files = len(self.json_audio_file_list)
                    print(f"Number of audio files to send: {number_of_files}")

                    # Tell node how many files to expect
                    sock.sendall(number_of_files.to_bytes(8, byteorder='big'))

                    # Send the list of audio files to chose from
                    audio_file_list = json.dumps(audio_file_paths)
                    sock.sendall(audio_file_list.encode())

                    authsub_message = sock.recv(1024).decode()
                    if authsub_message == "Ready to receive audio files":
                        file_index = 0

                        while file_index < number_of_files:
                            print(audio_file_paths[file_index])
                            with open("audio_files/using/" + audio_file_paths[file_index], 'rb') as file:
                                mp3_file_content = file.read()
                                md5_hash = hashlib.md5(mp3_file_content).hexdigest()

                            sock.sendall(len(mp3_file_content).to_bytes(8, byteorder='big'))
                            print(f"Sent file size: {len(mp3_file_content)}")
                            sock.sendall(mp3_file_content)
                            sock.sendall(md5_hash.encode())

                            fdn_sub_message = sock.recv(1024).decode()
                            if fdn_sub_message == "File received":
                                print(f"fdnSub: File {file_index} received")
                                file_index += 1
                    break
                else:
                    time.sleep(1)
            except socket.error as e:
                print(f"Socket error occurred: {e}")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")

        # Tell subFdns to start sending heartbeats
        sock.sendall(b"Start heartbeat")
        threading.Thread(target=self.handle_fdnSub_heartbeat, args=(sock,)).start()

    def handle_fdnSub_heartbeat(self, sock):
        while True:
            heartbeat_message = sock.recv(1024).decode()

            json_heartbeat = json.loads(heartbeat_message)

            # Get the ip and port of the fdnSub that sent the heartbeat
            hb_fdn_sub_ip = json_heartbeat[0]
            hb_fdn_sub_port = json_heartbeat[1]
            # Get the number of connected clients
            hb_num_of_connected_clients = int(json_heartbeat[2])

            print(f"\nhb_fdn_sub_ip: {hb_fdn_sub_ip}")
            print(f"hb_fdn_sub_port: {hb_fdn_sub_port}")
            print(f"hb_num_of_connected_clients: {hb_num_of_connected_clients}\n")
            print(f"subFdnWithLowestNumOfClients_numOfConnectedClients: {self.subFdnWithLowestNumOfClients_numOfConnectedClients}")

            print(f"Received heartbeat message from {hb_fdn_sub_ip}, {hb_fdn_sub_port}: {json_heartbeat}")

            if self.subFdnWithLowestNumOfClients_ip is None:
                self.subFdnWithLowestNumOfClients_ip = hb_fdn_sub_ip
                self.subFdnWithLowestNumOfClients_port = hb_fdn_sub_port
                self.subFdnWithLowestNumOfClients_numOfConnectedClients = hb_num_of_connected_clients
                print(f"New subFdn with lowest number of clients: {self.subFdnWithLowestNumOfClients_ip}, {self.subFdnWithLowestNumOfClients_port}, {self.subFdnWithLowestNumOfClients_numOfConnectedClients}")

            elif hb_fdn_sub_ip == self.subFdnWithLowestNumOfClients_ip and hb_fdn_sub_port == self.subFdnWithLowestNumOfClients_port:
                self.subFdnWithLowestNumOfClients_ip = hb_fdn_sub_ip
                self.subFdnWithLowestNumOfClients_port = hb_fdn_sub_port
                self.subFdnWithLowestNumOfClients_numOfConnectedClients = hb_num_of_connected_clients
                print(f"Updated values for subFdn with lowest number of clients: {self.subFdnWithLowestNumOfClients_ip}, {self.subFdnWithLowestNumOfClients_port}, {self.subFdnWithLowestNumOfClients_numOfConnectedClients}")

            elif hb_num_of_connected_clients < self.subFdnWithLowestNumOfClients_numOfConnectedClients:
                self.subFdnWithLowestNumOfClients_ip = hb_fdn_sub_ip
                self.subFdnWithLowestNumOfClients_port = hb_fdn_sub_port
                self.subFdnWithLowestNumOfClients_numOfConnectedClients = hb_num_of_connected_clients
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
                fdn_sub_ip_to_send = self.subFdnWithLowestNumOfClients_ip
                print(f"fdn_sub_ip_to_send: {fdn_sub_ip_to_send}")
                fdn_sub_port_to_send = self.subFdnWithLowestNumOfClients_port
                print(f"fdn_sub_port_to_send: {fdn_sub_port_to_send}")

                # Send the ip and port to the fdnSub
                sock.sendall(fdn_sub_ip_to_send.encode())
                print(f"Sent fdnSub ip: {fdn_sub_ip_to_send}")
                sock.sendall(fdn_sub_port_to_send.to_bytes(8, byteorder='big'))
                print(f"Sent fdnSub port: {fdn_sub_port_to_send}")

        except ConnectionResetError:
            print("Client disconnected unexpectedly.")
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            sock.close()
            print("Connection to client closed.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run FdnPrimary")
    parser.add_argument("ip", type=str, help="IP address to use")
    parser.add_argument("port", type=int, help="Port number to use")

    args = parser.parse_args()

    new_FdnPrimary = FdnPrimary(name="fdnPrimary")
    new_FdnPrimary.connect_to_bootstrap(args.ip, args.port)
