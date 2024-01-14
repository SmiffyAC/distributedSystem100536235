import socket
import json
import pygame
import hashlib


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
        self.token = None
        self.audio_file_list = []
        self.json_audio_file_list = []

        self.audio_file_size_list = []
        self.audio_file_data_list = []

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
            print(f"From BootStrap: {response}")

            if response == 'Welcome client':
                if self.token is None:
                    self.handle_auth(sock)
                else:
                    self.handle_fdn(sock)

    def handle_auth(self, sock):
        sock.sendall(b"authPrimary address")

        # Wait for auth address from server
        auth_primary_ip = sock.recv(1024).decode()
        print(f"From Bootstrap: Auth Primary address: {auth_primary_ip}")

        auth_primary_port = int.from_bytes(sock.recv(8), byteorder='big')
        print(f"From Bootstrap: Auth Primary port: {auth_primary_port}")

        self.connect_to_authPrimary(auth_primary_ip, auth_primary_port)

    def connect_to_authPrimary(self, auth_primary_ip, auth_primary_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((auth_primary_ip, auth_primary_port))

            print(f"Connected to Auth Primary at {auth_primary_ip}:{auth_primary_port}")

            # Tell the AuthPrimary that this is a client
            s.sendall(b"client")

            while True:
                # Get username and password from the user
                username = input("\nEnter your username: ")
                password = input("Enter your password: ")

                # Send the username and password to AuthPrimary
                s.sendall(username.encode())
                s.sendall(password.encode())

                # Receive response from AuthPrimary
                response = s.recv(1024).decode()
                print("\n** " + response + " **\n")

                if response == "Account created successfully.":
                    break
                elif response == "User found":
                    break

            # Ask for the authSub address
            s.sendall(b"Need authSub address")

            # Receive the authSub address
            authSub_ip = s.recv(1024).decode()
            print(f"From AuthPrimary: Auth Sub address = {authSub_ip}")
            authSub_port = int.from_bytes(s.recv(8), byteorder='big')
            print(f"From AuthPrimary: Auth Sub port = {authSub_port}")

            self.connect_to_authSub(authSub_ip, authSub_port)

    def connect_to_authSub(self, authSub_ip, authSub_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

            s.connect((authSub_ip, authSub_port))

            while True:
                s.sendall(b"client")

                authsub_message = s.recv(1024).decode()

                if authsub_message == "Ready to provide token":

                    s.sendall(b"token")

                    self.token = s.recv(1024).decode()

                    print(f"From Auth Sub: Received token = {self.token}")

                    if self.token is not None:
                        break

            self.connect_to_bootstrap(bootstrap_ip, bootstrap_port)

    def handle_fdn(self, sock):
        sock.sendall(b"fdnPrimary address")

        # Wait for fdn address from server
        fdn_primary_ip = sock.recv(1024).decode()
        print(f"From Bootstrap: Fdn Primary address = {fdn_primary_ip}")

        fdn_primary_port = int.from_bytes(sock.recv(8), byteorder='big')
        print(f"From Bootstrap: Fdn Primary port = {fdn_primary_port}")

        self.connect_to_fdnPrimary(fdn_primary_ip, fdn_primary_port)

    def connect_to_fdnPrimary(self, fdn_primary_ip, fdn_primary_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((fdn_primary_ip, fdn_primary_port))

            print(f"Connected to Fdn Primary at {fdn_primary_ip}:{fdn_primary_port}")

            # Tell the FDNPrimary that this is a client
            s.sendall(b"client")

            # Ask for the fdnSub address
            s.sendall(b"Need fdnSub address")

            # Receive the fdnSub address
            fdnSub_ip = s.recv(1024).decode()
            print(f"From FdnPrimary: Fdn Sub address = {fdnSub_ip}")
            fdnSub_port = int.from_bytes(s.recv(8), byteorder='big')
            print(f"From FdnPrimary: Fdn Sub port = {fdnSub_port}")

            self.connect_to_fdnSub(fdnSub_ip, fdnSub_port)

    def connect_to_fdnSub(self, fdnSub_ip, fdnSub_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

            s.connect((fdnSub_ip, fdnSub_port))

            while True:

                try:
                    s.sendall(b"client")

                    # FDNSUB will check token and send back a message
                    token_request = s.recv(1024).decode()

                    if token_request == "Please provide token":
                        s.sendall(self.token.encode())
                        print(f"Sent token: {self.token}")

                    fdnSub_message = s.recv(1024).decode()

                    if fdnSub_message == "Ready to provide songs":
                        s.sendall(b"song list")

                        audio_file_list = s.recv(1024).decode()
                        self.audio_file_list = audio_file_list
                        self.json_audio_file_list = json.loads(audio_file_list)

                        while True:
                            json_audio_file_list = json.loads(self.json_audio_file_list)

                            print(f"\nFrom Fdn Sub: Audio file list: \n{json_audio_file_list}\n")
                            song_choice = input("\nEnter the name of the song you would like to download: ")

                            song_index = json_audio_file_list.index(song_choice + ".mp3")
                            print(f"Index of chosen song = : {song_index}")

                            if song_choice in self.json_audio_file_list:
                                s.sendall(song_index.to_bytes(8, byteorder='big'))
                                break
                            else:
                                print("Song not found. Please try again.")
                                continue

                        audio_file_size_data = s.recv(8)
                        audio_file_size = int.from_bytes(audio_file_size_data, byteorder='big')
                        print(f"From Fdn Sub: Audio File size = {audio_file_size}")

                        mp3_data = b''
                        while len(mp3_data) < audio_file_size:
                            chunk = s.recv(min(4096, audio_file_size - len(mp3_data)))
                            if not chunk:
                                break
                            mp3_data += chunk

                        self.audio_file_size_list.append(audio_file_size)
                        print(self.audio_file_size_list)
                        self.audio_file_data_list.append(mp3_data)
                        received_md5_hash = s.recv(1024).decode()
                        print(f"\n** File received **\n")
                        print(f"\n From Fdn Sub: MD5 Hash for chosen song = {received_md5_hash}")

                        with open("Received " + song_choice + '.mp3', 'wb') as f:
                            f.write(mp3_data)
                            generated_md5_hash = hashlib.md5(mp3_data).hexdigest()
                            print(f"\nGenerated MD5 Hash from received file =  {generated_md5_hash}")

                            if received_md5_hash == generated_md5_hash:
                                print("\n** MD5 Hashes match **\n")
                            else:
                                print("\n** MD5 Hashes do not match - file may be corrupted **\n")

                        s.sendall(b"File received")

                        saved_song_name = "Received " + song_choice + '.mp3'
                        print(f"\n** Song saved as {saved_song_name} **\n")
                        s.close()
                        print("\n** Connection closed **\n")
                        # Play the song
                        self.play_song(saved_song_name)
                finally:
                    s.close()
                    break

    def play_song(self, song_path):
        # Initialize Pygame
        pygame.init()
        pygame.mixer.init()

        # Load and play the song
        pygame.mixer.music.load(song_path)
        pygame.mixer.music.play()

        print("Press 'SPACE' to pause/unpause or press 'q' to quit (then press enter)")

        running = True
        paused = False
        while running:

            if not paused:
                client_input = input("Press 'SPACE' to pause or 'q' to quit song (then press enter): ")
                if client_input == ' ':
                    paused = True
                    pygame.mixer.music.pause()
                    print("** PAUSED **")
                elif client_input == 'q':
                    running = False
            else:
                client_input = input("Press SPACE to unpause or 'q' to quit song (then press enter): ")
                if client_input == ' ':
                    paused = False
                    pygame.mixer.music.unpause()
                    print("** UNPAUSED **")
                elif client_input == 'q':
                    running = False

        print("\n** Song finished playing **\n")

        pygame.mixer.music.stop()
        pygame.quit()


if __name__ == '__main__':
    # Create a client instance with a unique name
    client = Client(name="client")
    # Connect the client to the Bootstrap Server
    bootstrap_ip = open('bootstrap_ip.txt', 'r').read().strip()
    bootstrap_port = 50000
    client.connect_to_bootstrap(bootstrap_ip, bootstrap_port)
