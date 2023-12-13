import socket
import threading
import json
import subprocess


class BootstrapServer:
    def __init__(self, port=50000):
        # self.host = '192.168.0.119'  # Set your server IP address
        # self.host = '172.26.61.101'  # IP ADDRESS AT LIBRARY
        # self.host = '192.168.56.1'  # IP ADDRESS AT MS
        self.host = open('bootstrap_ip.txt', 'r').read().strip()
        self.port = port
        self.connected_nodes = []  # List to store socket objects of connected nodes
        self.auth_primary_node = None  # Variable to store the authPrimary node
        self.auth_primary_node_ip = None  # Variable to store the authPrimary node IP
        self.fdn_primary_node = None  # Variable to store the fdnPrimary node
        self.subAuthNodes = []  # List to store the subAuth nodes
        self.subFdnNodes = []  # List to store the subFdn nodes
        self.nodes = {}  # Dictionary to store registered nodes
        self.client = None

    def start_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((self.host, self.port))
            sock.listen()
            print(f"Bootstrap Server listening on {self.host}:{self.port}")

            while True:
                node, addr = sock.accept()
                threading.Thread(target=self.handle_node, args=(node, addr)).start()

    def handle_node(self, node, addr):
        try:
            data = node.recv(1024).decode('utf-8')
            node_info = json.loads(data)
            if node_info['name'] == 'node':
                if len(self.connected_nodes) == 0:
                    self.auth_primary_node_ip = node_info['ip']
                self.connected_nodes.append(node)  # Store the socket object
                print(f"Connected nodes: {len(self.connected_nodes)}")
                self.nodes[node_info['name']] = (node_info['ip'], node_info['port'])
                print(f"Registered node: {node_info}")

                if len(self.connected_nodes) == 2:
                    self.reply_to_nodes()

            elif node_info['name'] == 'client':
                self.client = node
                self.reply_to_client()

        except Exception as e:
            print(f"Error: {e}")

    def reply_to_nodes(self):
        if self.connected_nodes:

            # HANDLE AUTH PRIMARY NODE
            self.auth_primary_node = self.connected_nodes[0]
            self.auth_primary_node.sendall(b"authPrimary")
            print(self.auth_primary_node)

            # Wait for confirmation from auth_primary_node
            confirmation = self.auth_primary_node.recv(1024).decode('utf-8')
            print(f"Confirmation received: {confirmation}")

            if confirmation == "authPrimary setup complete":
                # Send JSON data after confirmation
                self.subAuthNodes.append('subAuth1')
                self.subAuthNodes.append('subAuth2')
                auth_nodes_json = json.dumps(self.subAuthNodes)
                self.auth_primary_node.sendall(auth_nodes_json.encode('utf-8'))

                file_path = "clientLogins.txt"
                with open(file_path, 'r') as file:
                    file_content = file.read()
                    # encoded = base64.b64encode(data)
                    # self.auth_primary_node.sendall(encoded)
                    # print("File sent")
                self.auth_primary_node.sendall(file_content.encode('utf-8'))

            # HANDLE FDN PRIMARY NODE
            self.fdn_primary_node = self.connected_nodes[1]
            self.fdn_primary_node.sendall(b"fdnPrimary")

            # Wait for confirmation from auth_primary_node
            confirmation = self.fdn_primary_node.recv(1024).decode('utf-8')
            print(f"Confirmation received: {confirmation}")

            if confirmation == "fdnPrimary setup complete":
                # Send JSON data after confirmation
                self.subFdnNodes.append('subFdn1')
                self.subFdnNodes.append('subFdn2')
                fdn_nodes_json = json.dumps(self.subFdnNodes)
                self.fdn_primary_node.sendall(fdn_nodes_json.encode('utf-8'))

                mp3_file_path = "glossy.mp3"

                with open(mp3_file_path, 'rb') as file:
                    mp3_file_content = file.read()
                    # encoded = base64.b64encode(data)
                    # self.auth_primary_node.sendall(encoded)
                    # print("File sent")
                self.fdn_primary_node.sendall(len(mp3_file_content).to_bytes(8, byteorder='big'))
                self.fdn_primary_node.sendall(mp3_file_content)

            # Wait for confirmation from auth_primary_node
            confirmation = self.auth_primary_node.recv(1024).decode('utf-8')
            print(f"Confirmation received: {confirmation}")

    def reply_to_client(self):
        self.client.sendall(b"Welcome Client")

        # auth_data = json.loads(self.auth_primary_node)
        # auth_ip = auth_data['ip']

        self.client.sendall(self.auth_primary_node_ip.encode('utf-8'))


if __name__ == '__main__':
    server = BootstrapServer()
    server.start_server()
