import socket
import threading
import json

class BootstrapServer:
    def __init__(self, port=8000):
        self.host = '192.168.0.119'  # Set your server IP address
        self.port = port
        self.connected_nodes = []  # List to store socket objects of connected nodes
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
                    self.send_message_to_first_node()

        except Exception as e:
            print(f"Error: {e}")

    def send_message_to_first_node(self):
        if self.connected_nodes:
            first_node = self.connected_nodes[0]
            first_node.sendall(b"authPrimary")

if __name__ == '__main__':
    server = BootstrapServer()
    server.start_server()
