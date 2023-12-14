import socket
import threading
import json
import subprocess


class BootstrapServer:
    def __init__(self, port=50000):
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
                threading.Thread(target=self.handle_connection, args=(node, addr)).start()

    def handle_connection(self, node, addr):
        try:
            data = node.recv(1024).decode('utf-8')
            node_info = json.loads(data)

            if node_info['name'] == 'node':
                self.handle_node(node, node_info)

            elif node_info['name'] == 'authPrimary':
                self.handle_auth_primary(node, node_info)

            elif node_info['name'] == 'fdnPrimary':
                self.handle_fdn_primary(node, node_info)

            elif node_info['name'] == 'client':
                self.handle_client(node, node_info)

        except Exception as e:
            print(f"Error: {e}")

    def handle_node(self, node, node_info):

        # Tell the first connected node to be authPrimary
        if len(self.connected_nodes) == 0:
            print("Length of connected nodes: ")
            print(len(self.connected_nodes))
            node.sendall(b"authPrimary")
            self.connected_nodes.append(node)  # Store the socket object
            print(f"Node handling authPrimary creation: {node_info['ip'], node_info['port']}")
            self.auth_primary_node_ip = (node_info['ip'])
            print(f"Auth Primary Node IP: {self.auth_primary_node_ip}")

        elif len(self.connected_nodes) == 1:
            print("Length of connected nodes: ")
            print(len(self.connected_nodes))
            node.sendall(b"fdnPrimary")
            self.connected_nodes.append(node)  # Store the socket object
            print(f"Node handling fdnPrimary creation: {node_info['ip'], node_info['port']}")

        else:
            node.sendall(b"sub")
            self.connected_nodes.append(node)  # Store the socket object
            print(f"Node handling a sub creation: {node_info['ip'], node_info['port']}")

    def handle_auth_primary(self, sock, node_info):

        print(f"In handle_auth_primary")

        # Send JSON data
        self.subAuthNodes.append('subAuth1')
        self.subAuthNodes.append('subAuth2')
        auth_nodes_json = json.dumps(self.subAuthNodes)
        print(f"Auth Nodes JSON to send: {auth_nodes_json}")
        sock.sendall(auth_nodes_json.encode('utf-8'))

        file_path = "clientLogins.txt"
        with open(file_path, 'r') as file:
            file_content = file.read()

        print(f"File content to send: {file_content}")
        sock.sendall(file_content.encode('utf-8'))

    def handle_fdn_primary(self, sock, node_info):

        print(f"In handle_fdn_primary")

        # Send JSON data after confirmation
        self.subFdnNodes.append('subFdn1')
        self.subFdnNodes.append('subFdn2')
        fdn_nodes_json = json.dumps(self.subFdnNodes)
        sock.sendall(fdn_nodes_json.encode('utf-8'))

        audio_file_paths = ["glossy.mp3", "relaxing.mp3", "risk.mp3"]

        number_of_files = len(audio_file_paths)
        print(f"Number of audio files to send: {number_of_files}")

        # Tell node how many files to expect
        sock.sendall(number_of_files.to_bytes(8, byteorder='big'))

        file_index = 0

        while file_index < number_of_files:
            print(audio_file_paths[file_index])
            with open(audio_file_paths[file_index], 'rb') as file:
                mp3_file_content = b''
                mp3_file_content = file.read()

            sock.sendall(len(mp3_file_content).to_bytes(8, byteorder='big'))
            print(f"Sent file size: {len(mp3_file_content)}")
            sock.sendall(mp3_file_content)
            file_index += 1

    def handle_client(self, sock, node_info):
        pass


if __name__ == '__main__':
    server = BootstrapServer()
    server.start_server()
