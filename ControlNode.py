import socket
import json
import subprocess


class ControlNode:
    def __init__(self, name):
        # Initialize the client with a name, host, and port
        node_name = socket.gethostname()
        node_ip = socket.gethostbyname(node_name)
        self.name = name
        self.host = node_ip
        # self.port = self.find_open_port()

    def connect_to_bootstrap(self, bootstrap_host, bootstrap_port):
        # Connect to the Bootstrap Server
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((bootstrap_host, bootstrap_port))
            # Prepare the client information as JSON
            client_info = {"name": self.name, "ip": self.host}
            # Send the client information to the Bootstrap Server
            sock.sendall(json.dumps(client_info).encode('utf-8'))
            print(f"Connected to Bootstrap Server and sent info: {client_info}")


if __name__ == '__main__':
    # Create a client instance with a unique name
    control_node = ControlNode(name="controlNode")
    # Connect the client to the Bootstrap Server
    bootstrap_ip = open('bootstrap_ip.txt', 'r').read().strip()
    control_node.connect_to_bootstrap(bootstrap_ip, 50000)
