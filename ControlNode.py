import socket
import json
import subprocess
import sys
import time
import threading


class ControlNode:
    def __init__(self, name):
        # Initialize the control node with a name and host
        node_name = socket.gethostname()
        hostname, aliases, ip_addresses = socket.gethostbyname_ex(node_name)

        # Filter for IP addresses that start with '10'
        ip_address_10 = next((ip for ip in ip_addresses if ip.startswith('10')), None)
        node_name = socket.gethostname()
        node_ip = socket.gethostbyname(node_name)
        self.name = name
        self.host = ip_address_10
        self.port = self.find_open_port()
        self.retry_delay = 5  # seconds for retrying connection
        self.max_retries = 5  # maximum number of retry attempts
        self.instance_creation_delay = 5  # seconds delay between node instance creations

    def find_open_port(self):
        # Iterate through the port range to find the first open port
        port_range = (50001, 50010)
        for port in range(port_range[0], port_range[1] + 1):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                if sock.connect_ex((self.host, port)) != 0:
                    # Port is open, use this one
                    return port
        raise Exception("No open ports available in the specified range.")

    def accept_connections(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((self.host, self.port))
            sock.listen()
            print(f"controlNode now listening on {self.host}:{self.port}")

            while True:
                node, addr = sock.accept()

                initial_message = node.recv(1024).decode()

                if initial_message == "authSub":
                    print(f"Received connection from {addr} asking to start an authSub")
                    node.sendall(b"Address and Port")
                    authPrimary_ip = node.recv(1024).decode()
                    print(f"Received authPrimary address: {authPrimary_ip}")
                    authPrimary_port = int.from_bytes(node.recv(8), byteorder='big')
                    print(f"Received authPrimary port: {authPrimary_port}")
                    threading.Thread(target=self.handle_subAuth_creation, args=(authPrimary_ip, authPrimary_port, 0)).start()
                elif initial_message == "fdnSub":
                    print(f"Received connection from {addr} asking to start an fdnSub")
                    node.sendall(b"Address and Port")
                    fdnPrimary_ip = node.recv(1024).decode()
                    print(f"Received fdnPrimary address: {fdnPrimary_ip}")
                    fdnPrimary_port = int.from_bytes(node.recv(8), byteorder='big')
                    print(f"Received fdnPrimary port: {fdnPrimary_port}")
                    threading.Thread(target=self.handle_subFdn_creation, args=(fdnPrimary_ip, fdnPrimary_port, 0)).start()
                else:
                    node.close()

    def connect_to_bootstrap(self, bootstrap_host, bootstrap_port):
        # Retry mechanism for connecting to the Bootstrap Server
        for attempt in range(self.max_retries):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.connect((bootstrap_host, bootstrap_port))
                    # Prepare the client information as JSON
                    client_info = {"name": self.name, "ip": self.host, "port": self.port}
                    # Send the client information to the Bootstrap Server
                    sock.sendall(json.dumps(client_info).encode('utf-8'))
                    print(f"Connected to Bootstrap Server and sent info: {client_info}")
                    self.listen_for_instructions(sock)
                    break  # Break the loop if connection is successful
            except ConnectionRefusedError:
                print(f"Connection attempt {attempt + 1} failed. Retrying in {self.retry_delay} seconds...")
                time.sleep(self.retry_delay)

    def listen_for_instructions(self, sock):
        # Listen for instructions from the Bootstrap server
        while True:
            data = sock.recv(1024).decode('utf-8')
            if not data:
                break
            self.handle_instruction(data)

    def handle_instruction(self, instruction):
        # Parse the instruction
        instruction_data = json.loads(instruction)

        # Check the type of instruction
        if instruction_data.get('command') == 'start_nodes':
            num_instances = instruction_data.get('num_instances')
            self.instance_creation_delay = instruction_data.get('delay', 0)

            print(f"Starting {num_instances} node instances after a delay of {self.instance_creation_delay} seconds.")
            for _ in range(num_instances):
                time.sleep(self.instance_creation_delay)
                self.start_node_instance()
        elif instruction_data.get('command') == 'start_PrimaryAuth':
            print("FROM BOOTSTRAP: start_PrimaryAuth")
            self.handle_authPrimary_creation()

        elif instruction_data.get('command') == 'start_PrimaryFdn':
            print("FROM BOOTSTRAP: start_PrimaryFdn")
            self.handle_fdnPrimary_creation()

    def start_node_instance(self):
        # Logic to start a node.py instance
        print("Starting a node.py instance...")
        pid = subprocess.Popen([sys.executable, "node.py"],
                               creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NEW_CONSOLE).pid

    def handle_authPrimary_creation(self):
        print(f"Starting authPrimary.py and passing BS addr of {bootstrap_ip} and port {50000}")

        pid = subprocess.Popen([sys.executable, "authPrimary.py", str(bootstrap_ip), str(50000)],
                               creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NEW_CONSOLE).pid

    def handle_fdnPrimary_creation(self):
        print(f"Starting fdnPrimary.py and passing BS addr of {bootstrap_ip} and port {50000}")

        pid = subprocess.Popen([sys.executable, "fdnPrimary.py", str(bootstrap_ip), str(50000)],
                               creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NEW_CONSOLE).pid

    def handle_subAuth_creation(self, authPrimary_ip, authPrimary_port, delay):

        # Delay
        time.sleep(delay)

        print(f"Starting authSub.py")

        pid = subprocess.Popen([sys.executable, "authSub.py", str(authPrimary_ip), str(authPrimary_port)],
                               creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NEW_CONSOLE).pid

    def handle_subFdn_creation(self, fdnPrimary_ip, fdnPrimary_port, delay):

        # Delay
        time.sleep(delay)

        print(f"Starting fdnSub.py")

        pid = subprocess.Popen([sys.executable, "fdnSub.py", str(fdnPrimary_ip), str(fdnPrimary_port)],
                               creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NEW_CONSOLE).pid


if __name__ == '__main__':
    # Create a control node instance with a unique name
    control_node = ControlNode(name="controlNode")
    # Connect the control node to the Bootstrap Server
    bootstrap_ip = open('bootstrap_ip.txt', 'r').read().strip()
    print("cheese")
    threading.Thread(target=control_node.accept_connections).start()
    print("burger")
    control_node.connect_to_bootstrap(bootstrap_ip, 50000)
    print("wakka")
