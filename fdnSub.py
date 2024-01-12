import socket
import json
import subprocess
import base64
import threading
import argparse
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
        self.audio_file_list = []
        self.json_audio_file_list = []

        self.audio_file_size_list = []
        self.audio_file_data_list = []
        self.md5_hash_list = []

        print(f"FdnSub set up on: {self.host}, Node Port: {self.port}")

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
            self.audio_file_list = audio_file_list
            print(f"FROM BOOSTRAP - Audio file list: {self.audio_file_list}")
            self.json_audio_file_list = json.loads(audio_file_list)
            print(f"FROM BOOTSTRAP - JSON audio file list: {self.json_audio_file_list}")

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
                print(md5_hash)
                self.md5_hash_list.append(md5_hash)
                print(f"MD5_hash_list: {self.md5_hash_list}")
                print(f"File {file} received")
                sock.sendall(b"File received")
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
                fdnSub_ip = self.host
                s.sendall(fdnSub_ip.encode())
                print(f"Sent FdnSub address: {self.host}")
                fdnSub_port = self.port
                s.sendall(fdnSub_port.to_bytes(8, byteorder='big'))
                print(f"Sent FdnSub port: {self.port}")

            # Receive the audio files from the Fdn Primary

            self.number_of_files = int.from_bytes(s.recv(8), byteorder='big')
            print(f"Expected number of audio files: {self.number_of_files}")

            audio_file_list = s.recv(1024).decode()
            print(f"Received audio file list: {audio_file_list}")
            self.audio_file_list = audio_file_list
            print(f"FROM FDNPRIMARY - Audio file list: {self.audio_file_list}")
            self.json_audio_file_list = json.loads(audio_file_list)
            print(f"FROM FDNPRIMARY - JSON audio file list: {self.json_audio_file_list}")

            s.sendall(b"Ready to receive audio files")
            print(f"Sent ready to receive audio files message")

            file = 0

            while file < self.number_of_files:
                audio_file_size_data = s.recv(8)
                audio_file_size = int.from_bytes(audio_file_size_data, byteorder='big')
                print(f"Audio File size: {audio_file_size}")

                mp3_data = b''
                while len(mp3_data) < audio_file_size:
                    chunk = s.recv(min(4096, audio_file_size - len(mp3_data)))
                    if not chunk:
                        break
                    mp3_data += chunk

                self.audio_file_size_list.append(audio_file_size)
                print(self.audio_file_size_list)
                self.audio_file_data_list.append(mp3_data)
                md5_hash = s.recv(1024)
                print(md5_hash)
                self.md5_hash_list.append(md5_hash)
                print(f"MD5_hash_list: {self.md5_hash_list}")
                print(f"File {file} received")
                s.sendall(b"File received")
                file += 1

            fdnPrimary_message_2 = s.recv(1024).decode()

            if fdnPrimary_message_2 == "Start heartbeat":
                self.send_heartbeat_to_fdnPrimary(s)

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
            time.sleep(10)


    def handle_client_connection(self):
        print(f"IN HANDLE_CLIENT_CONNECTION - Inside thread for handle_client_connection")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((self.host, self.port))
            sock.listen()
            print(f"fdnSub now listening for clients on {self.host}:{self.port}")

            while True:
                node, addr = sock.accept()

                try:
                    connection_message = node.recv(1024).decode()
                    if connection_message == 'client':
                        print(f"Accepted connection from client with info: {addr}")
                        self.numOfConnectedClients += 1

                        # Ask for token
                        node.sendall(b"Please provide token")

                        client_token = node.recv(1024).decode()

                        if self.check_token(client_token):
                            node.sendall(b"Ready to provide songs")

                            client_message = node.recv(1024).decode()
                            print(f"Received message from client: {client_message}")

                            if client_message == 'song list':
                                audio_file_paths = self.audio_file_list
                                print(f"Audio file paths: {audio_file_paths}")
                                audio_file_list = json.dumps(audio_file_paths)
                                print(f"Audio file list: {audio_file_list}")
                                node.sendall(audio_file_list.encode())
                                print(f"Sent song list to client: {audio_file_list}")

                                song_index = int.from_bytes(node.recv(8), byteorder='big')
                                print(f"Song index: {song_index}")

                                node.sendall(self.audio_file_size_list[song_index].to_bytes(8, byteorder='big'))
                                print(f"Sent song size: {self.audio_file_size_list[song_index]}")
                                node.sendall(self.audio_file_data_list[song_index])
                                print(f"Sent song data")
                                node.sendall(self.md5_hash_list[song_index])
                                print(f"Sent md5 hash {self.md5_hash_list[song_index]}")

                                final_message = node.recv(1024).decode()
                                if final_message == "File received":
                                    print(f"\n** Client received file - Closing connection with client **\n")
                                    node.close()
                                    self.numOfConnectedClients -= 1
                        else:
                            node.sendall(b"Invalid token")
                            print(f"Invalid token")
                            node.close()
                            self.numOfConnectedClients -= 1

                    else:
                        node.close()

                except:
                    print("\n** Client disconnected unexpectedly. **")
                    self.numOfConnectedClients -= 1
                    print(f"Number of connected clients change to: {self.numOfConnectedClients}")
                    print("** Connection with client closed. **\n")

                finally:
                    node.close()


    def check_token(self, token):

        parts = token.split('|')

        ip_from_token = parts[0]
        port_from_token = int(parts[1])

        print(f"IP from token: {ip_from_token}")
        print(f"Port from token: {port_from_token}")

        # Connect to the necessary authSub
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((ip_from_token, port_from_token))

            sock.sendall(b"fdnSub")

            authsub_message = sock.recv(1024).decode()

            if authsub_message == "Ready to receive token":
                # Send the token to the authSub
                sock.sendall(token.encode())
                print(f"Sent token to authSub: {token}")

                # Receive the response from the authSub
                authSub_response = sock.recv(1024).decode()
                print(f"Received response from authSub: {authSub_response}")

                if authSub_response == "Valid token":
                    print(f"\n**TOKEN IS VALID**\n")
                    return True
                else:
                    return False


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Run AuthSub")
    parser.add_argument("ip", type=str, help="IP address to use")
    parser.add_argument("port", type=int, help="Port number to use")

    args = parser.parse_args()

    new_FdnSub = FdnSub(name="fdnSub")
    threading.Thread(target=new_FdnSub.handle_client_connection).start()
    new_FdnSub.connect_to_fdnPrimary(args.ip, args.port)
