import socket
import sys


class AuthPrimary:
    def __init__(self, name):
        # Initialize the client with a name, host, and port
        node_name = socket.gethostname()
        node_ip = socket.gethostbyname(node_name)
        self.name = name
        self.host = node_ip
        self.port = self.find_open_port()
        print(f"AuthPrimary set up on - Node IP: {self.host}, Node Port: {self.port}")

    def find_open_port(self):
        # Iterate through the port range to find the first open port
        port_range = (50001, 50010)
        for port in range(port_range[0], port_range[1] + 1):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                if sock.connect_ex((self.host, port)) != 0:
                    # Port is open, use this one
                    return port
        raise Exception("No open ports available in the specified range.")

    def connect_to_founding_node(self, node_ip, node_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((node_ip, node_port))
            print(f"22222 AuthPrimary set up on - Node IP: {self.host}, Node Port: {self.port}")
            # Ready to receive data
            print("Connected to node at " + node_ip + ":" + str(node_port))

            while True:
                s.sendall(b"authPrimary process has been created")

                client_list_data = s.recv(1024).decode()
                print(f"Received list data: {client_list_data}")

                client_file_data = s.recv(1024).decode()
                print(f"Received file data: {client_file_data}")

                s.sendall(b"I have received the data")


if __name__ == '__main__':

    AuthPrimary = AuthPrimary(name="authPrimary")

    AuthPrimary.connect_to_founding_node(sys.argv[1], int(sys.argv[2]))

