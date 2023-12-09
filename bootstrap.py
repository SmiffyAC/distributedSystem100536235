import socket
import threading
import json
import base64


class BootstrapServer:
    def __init__(self, port=8000):
        self.host = '192.168.0.119'  # Set your server IP address
        self.port = port
        self.connected_nodes = []  # List to store socket objects of connected nodes
        self.auth_primary_node = None  # Variable to store the authPrimary node
        self.fdn_primary_node = None  # Variable to store the fdnPrimary node
        self.subAuthNodes = []  # List to store the subAuth nodes
        self.subFdnNodes = []  # List to store the subFdn nodes
        self.nodes = {}  # Dictionary to store registered nodes

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
                self.connected_nodes.append(node)  # Store the socket object
                print(f"Connected nodes: {len(self.connected_nodes)}")
                self.nodes[node_info['name']] = (node_info['ip'], node_info['port'])
                print(f"Registered node: {node_info}")

                if len(self.connected_nodes) == 2:
                    self.reply_to_nodes()

        except Exception as e:
            print(f"Error: {e}")

    def reply_to_nodes(self):
        if self.connected_nodes:

            self.auth_primary_node = self.connected_nodes[0]
            self.auth_primary_node.sendall(b"authPrimary")

            # Wait for confirmation from auth_primary_node
            confirmation = self.auth_primary_node.recv(1024).decode('utf-8')
            print(f"Confirmation received: {confirmation}")

            if confirmation == "authPrimary setup complete":
                # Send JSON data after confirmation
                self.subAuthNodes.append('subAuth1')
                self.subAuthNodes.append('subAuth2')
                auth_nodes_json = json.dumps(self.subAuthNodes)
                self.auth_primary_node.sendall(auth_nodes_json.encode('utf-8'))

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

            # Wait for confirmation from auth_primary_node
            confirmation = self.auth_primary_node.recv(1024).decode('utf-8')
            print(f"Confirmation received: {confirmation}")


if __name__ == '__main__':
    server = BootstrapServer()
    server.start_server()
