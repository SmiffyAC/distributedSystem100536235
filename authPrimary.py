import socket
import json
import threading
import argparse
import time
import random


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

        self.control_node_ips = []  # List to store the control node IPs
        self.control_node_ports = []  # List to store the control node ports

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

            if sock.recv(1024).decode() == "Ready to provide controlNode list":
                # Receive the control node ips
                self.control_node_ips = json.loads(sock.recv(1024).decode())
                print(f"Received controlNode ips: {self.control_node_ips}")
                self.control_node_ports = json.loads(sock.recv(1024).decode())
                print(f"Received controlNode ports: {self.control_node_ports}")

            self.authSub_file = sock.recv(1024).decode()
            print(f"Received file data: {self.authSub_file}")

            self.generate_auth_subs()

    def generate_auth_subs(self):
        # While two authSubs have not been created, generate one
        num_generated = 0
        while num_generated < 2:
            random_control_node_index = random.randint(0, len(self.control_node_ips) - 1)
            control_node_ip = self.control_node_ips[random_control_node_index]
            print(f"random_control_node_ip: {control_node_ip}")
            control_node_port = self.control_node_ports[random_control_node_index]
            print(f"random_control_node_port: {control_node_port}")

            # Create the authSub
            threading.Thread(target=self.connect_to_control_node, args=(control_node_ip, control_node_port)).start()
            num_generated += 1
            time.sleep(1)


    def connect_to_control_node(self, control_node_ip, control_node_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((control_node_ip, control_node_port))

            sock.send(b"authSub")

            if sock.recv(1024).decode() == "Address and Port":
                sock.sendall(self.host.encode())
                print(f"Sent AuthPrimary address: {self.host}")
                sock.sendall(self.port.to_bytes(8, byteorder='big'))
                print(f"Sent AuthPrimary port: {self.port}")



    def accept_client_connection(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((self.host, self.port))
            sock.listen()
            print(f"authPrimary now listening on {self.host}:{self.port}")

            while True:
                node, addr = sock.accept()

                connection_message = node.recv(1024).decode()

                if connection_message == 'authSub':
                    print(f"\nAccepted connection from {addr}")
                    print(f"Received connection message: {connection_message}")
                    threading.Thread(target=self.handle_authSub_connection, args=(node, addr)).start()
                elif connection_message == 'client':
                    print(f"\nAccepted connection from {addr}")
                    print(f"Received connection message: {connection_message}")
                    threading.Thread(target=self.handle_client_connection, args=(node,)).start()
                else:
                    node.close()

    def handle_authSub_connection(self, sock, addr):

        print(f"\nA new authSub has connected from: {addr}")
        self.numOfAuthSubs += 1
        print(f"Number of authSubs: {self.numOfAuthSubs}")

        while True:
            try:
                if self.numOfAuthSubs == 2:
                    # Receive the authSub address and port
                    sock.sendall(b"Address and Port")
                    print(f"Asked subAuth for address and port - NUMOFSUBAUTHS = {self.numOfAuthSubs}")

                    self.authSub_ip = sock.recv(1024).decode()
                    print(f"Received authSub address: {self.authSub_ip}")
                    self.authSub_port = int.from_bytes(sock.recv(8), byteorder='big')
                    print(f"Received authSub port: {self.authSub_port}")
                    break
                else:
                    print(f"Waiting for second authSub to connect - NUMOFSUBAUTHS = {self.numOfAuthSubs}")
                    time.sleep(1)
            except:
                pass

        # Tell subAuths to start sending heartbeats
        sock.sendall(b"Start heartbeat")
        # self.handle_authSub_heartbeat(sock, addr)
        threading.Thread(target=self.handle_authSub_heartbeat, args=(sock, addr)).start()

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


            time.sleep(5)

    def handle_client_connection(self, sock):

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

            # Send the ip and port to the authSub
            sock.sendall(authsub_ip_to_send.encode())
            print(f"Sent authSub ip: {authsub_ip_to_send}")
            sock.sendall(authsub_port_to_send.to_bytes(8, byteorder='big'))
            print(f"Sent authSub port: {authsub_port_to_send}")


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Run AuthPrimary")
    parser.add_argument("ip", type=str, help="IP address to use")
    parser.add_argument("port", type=int, help="Port number to use")

    args = parser.parse_args()

    new_AuthPrimary = AuthPrimary(name="authPrimary")
    new_AuthPrimary.connect_to_bootstrap(args.ip, args.port)
