import socket
import json
import subprocess


class Node:
    def __init__(self, name, host='localhost', port=9000):
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

            response = sock.recv(1024).decode()
            print(f"Received response: {response}")

            if response == "authPrimary":
                self.handle_auth_primary(sock)

            elif response == "fdnPrimary":
                self.handle_fdn_primary(sock)

    def handle_auth_primary(self, sock):
        # Start authPrimary.py process
        process = subprocess.Popen(["python", "authPrimary.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   text=True)

        # Send confirmation back to Bootstrap Server
        sock.sendall(b"authPrimary setup complete")

        # Wait for list from server
        list_data = sock.recv(1024).decode()
        print(f"Received list data: {list_data}")

        file_data = sock.recv(1024).decode()
        print(f"Received file data: {file_data}")

        process.stdin.write("ACTION1" + list_data)
        process.stdin.flush()

        process.stdin.write("ACTION2" + file_data)
        process.stdin.flush()

        process.stdin.close()


    def handle_fdn_primary(self, sock):
        # Start fdnPrimary.py process
        process = subprocess.Popen(["python", "fdnPrimary.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   text=True)

        # Send confirmation back to Bootstrap Server
        sock.sendall(b"fdnPrimary setup complete")

        # Wait for list from server
        list_data = sock.recv(1024).decode()
        print(f"Received list data: {list_data}")

        # Pass the list data to authPrimary.py subprocess
        # process.stdin.write(list_data)

        # Pass the list data to authPrimary.py subprocess and capture output
        # output, _ = process.communicate(input=list_data)
        # print(f"Output from fdnPrimary.py: {output}")

        # file_data = sock.recv(1024).decode()
        # print(f"Received file data: {file_data}")

        process.stdin.write("ACTION1" + list_data)
        # process.stdin.write("ACTION2" + file_data)

        process.stdin.close()


if __name__ == '__main__':
    # Create a client instance with a unique name
    client = Node(name="node")
    # Connect the client to the Bootstrap Server
    bootstrap_ip = '192.168.0.119'
    client.connect_to_bootstrap(bootstrap_ip, 8000)
