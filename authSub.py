import argparse
import socket
import json
import sys
import threading
import time


class AuthSub:
    def __init__(self, name):
        # Initialize the client with a name, host, and port
        node_name = socket.gethostname()
        hostname, aliases, ip_addresses = socket.gethostbyname_ex(node_name)
        # Filter for IP addresses that start with 10
        ip_address_10 = next((ip for ip in ip_addresses if ip.startswith('10')), None)
        self.name = name
        self.host = ip_address_10
        self.port = self.find_open_port()
        self.tokenSet = set()   # set of tokens
        self.numOfConnectedClients = 0  # number of connected clients
        print(f"AuthSub set up on: {self.host}, Node Port: {self.port}")

    def find_open_port(self):
        # Iterate through the port range to find the first open port
        port_range = (50001, 50010)
        for port in range(port_range[0], port_range[1]):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                if sock.connect_ex((self.host, port)) != 0:
                    # Port is open, use this one
                    return port
        raise Exception("No open ports available in the specified range.")

    def connect_to_authPrimary(self, auth_primary_ip, auth_primary_port):
        # Connect to the authPrimary
        print(f"\nWaiting for authPrimary to be ready at {auth_primary_ip}:{auth_primary_port}")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

            s.connect((auth_primary_ip, auth_primary_port))

            s.sendall(b"authSub")

            print(f"Connected to Auth Primary at {auth_primary_ip}:{auth_primary_port}")

            auth_primary_message = s.recv(1024).decode()
            print(f"Received message from Auth Primary: {auth_primary_message}")
            # Provide the authPrimary with the address and port of the authSub
            if auth_primary_message == "Address and Port":
                auth_sub_ip = self.host
                s.sendall(auth_sub_ip.encode())
                print(f"Sent AuthSub address: {self.host}")
                auth_sub_port = self.port
                s.sendall(auth_sub_port.to_bytes(8, byteorder='big'))
                print(f"Sent AuthSub port: {self.port}")

            auth_primary_message_2 = s.recv(1024).decode()

            if auth_primary_message_2 == "Start heartbeat":
                print("\n ** Heartbeat started **")
                self.send_heartbeat_to_authPrimary(s)

    def send_heartbeat_to_authPrimary(self, s):
        # Send heartbeat to authPrimary
        time.sleep(5)
        while True:
            heartbeat_list = [self.host, self.port, self.numOfConnectedClients]

            heartbeat = json.dumps(heartbeat_list)
            print(f"Heartbeat Sent: {heartbeat}")
            try:
                s.sendall(heartbeat.encode())
            except socket.error as e:
                # If the heartbeat send fails, close the program
                print(f"Failed to send heartbeat: {e}")
                print(f"Closing program due to failed heartbeat send in 2 seconds.")
                time.sleep(2)
                sys.exit("Closing program due to failed heartbeat send.")

            time.sleep(10)

    def accept_client_connection(self):
        # Accept client connections
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((self.host, self.port))
            sock.listen()
            print(f"authSub now listening for clients on {self.host}:{self.port}")

            while True:
                node, addr = sock.accept()

                connection_message = node.recv(1024).decode()

                if connection_message == 'client':
                    print(f"Accepted connection from client with info: {addr}")
                    # Start a thread to handle the client connection
                    client_thread = threading.Thread(target=self.handle_client_connection, args=(node,))
                    client_thread.daemon = True
                    client_thread.start()

                elif connection_message == 'fdnSub':
                    print(f"Accepted connection from client with info: {addr}")
                    # Start a thread to handle the fdnSub connection
                    fdn_sub_thread = threading.Thread(target=self.handle_fdnSub_connection, args=(node,))
                    fdn_sub_thread.daemon = True
                    fdn_sub_thread.start()

    def handle_client_connection(self, node):

        node.sendall(b"Ready to provide token")

        client_message = node.recv(1024).decode()
        print(f"Received message from client: {client_message}")

        # Provide the client with a token
        if client_message == 'token':
            time_stamp = str(time.time())
            token = str(self.host) + "|" + str(self.port) + "|" + time_stamp
            print(f"Token: {token}")
            node.sendall(token.encode())
            print(f"Sent token: {token}")
            self.tokenSet.add(token)
            print(f"Token Set: {self.tokenSet}")

    def handle_fdnSub_connection(self, node):

        node.sendall(b"Ready to receive token")

        received_token = node.recv(1024).decode()

        print(f"Received token: {received_token}")

        # Check if the token provided by fdnSub is valid
        if received_token in self.tokenSet:
            node.sendall(b'Valid token')
            print(f"\n**VALID TOKEN**\n")
        else:
            node.sendall(b'Invalid token')
            print(f"Invalid token")


if __name__ == '__main__':
    # Parse the command line arguments
    parser = argparse.ArgumentParser(description="Run AuthSub")
    parser.add_argument("ip", type=str, help="IP address to use")
    parser.add_argument("port", type=int, help="Port number to use")
    args = parser.parse_args()
    # Start the authSub
    new_AuthSub = AuthSub(name="authSub")
    # Start a thread to accept client connections
    connections_thread = threading.Thread(target=new_AuthSub.accept_client_connection)
    connections_thread.daemon = True
    connections_thread.start()
    # Connect to the authPrimary
    new_AuthSub.connect_to_authPrimary(args.ip, args.port)
