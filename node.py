import socket
import json

class Node:
    def __init__(self, name, port=8080):
        # Initialize the client with a name, host, and port
        node_name = socket.gethostname()
        node_ip = socket.gethostbyname(node_name)
        self.name = name
        self.host = node_ip
        self.port = port

    def connect_to_bootstrap(self, bootstrap_host, bootstrap_port):
        # Connect to the Bootstrap Server
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((bootstrap_host, bootstrap_port))
            # Prepare the client information as JSON
            client_info = {"name": self.name, "ip": self.host, "port": self.port}
            # Send the client information to the Bootstrap Server
            sock.sendall(json.dumps(client_info).encode('utf-8'))
            print(f"Connected to Bootstrap Server and sent info: {client_info}")

            # Wait for a response from the server
            response = sock.recv(1024)
            print(f"Received response: {response.decode()}")

if __name__ == '__main__':
    # Create a client instance with a unique name
    client = Node(name="node")
    # Connect the client to the Bootstrap Server
    bootstrap_ip = '192.168.0.119'
    client.connect_to_bootstrap(bootstrap_ip, 8000)
