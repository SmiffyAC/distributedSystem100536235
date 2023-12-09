import socket
import threading
import json

class BootstrapServer:
    def __init__(self, port=8000):
        # Initialize server with host and port
        hostname = socket.gethostname()
        host_ip = socket.gethostbyname(hostname)
        self.host = host_ip
        self.port = port
        # Set to store connected node addresses
        self.connected_nodes = set()
        # Dictionary to store registered nodes
        self.nodes = {}

    def start_server(self):
        # Create a TCP/IP socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            # Bind the socket to the host and port
            sock.bind((self.host, self.port))
            # Listen for incoming connections
            sock.listen()
            print(f"Bootstrap Server listening on {self.host}:{self.port}")

            while True:
                # Accept new connection
                node, addr = sock.accept()
                # Handle each node connection in a new thread
                threading.Thread(target=self.handle_node, args=(node, addr)).start()

    def handle_node(self, node, addr):
        try:
            # Receive data from node
            data = node.recv(1024).decode('utf-8')
            # Decode data to JSON
            node_info = json.loads(data)
            # Check if the node name is 'node' and add to the set
            if node_info['name'] == 'node':
                self.connected_nodes.add(addr)
                print(f"Connected node: {addr}")
                print(f"Connected nodes: {self.connected_nodes}")
            # Register node information
            self.nodes[node_info['name']] = (node_info['ip'], node_info['port'])
            print(f"Registered node: {node_info}")
        finally:
            # Close the connection
            node.close()


if __name__ == '__main__':
    server = BootstrapServer()
    server.start_server()
