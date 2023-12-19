import socket
import json
import subprocess
import sys
import time

class ControlNode:
    def __init__(self, name):
        # Initialize the control node with a name and host
        node_name = socket.gethostname()
        node_ip = socket.gethostbyname(node_name)
        self.name = name
        self.host = node_ip
        self.retry_delay = 5  # seconds for retrying connection
        self.max_retries = 5  # maximum number of retry attempts
        self.instance_creation_delay = 5  # seconds delay between node instance creations

    def connect_to_bootstrap(self, bootstrap_host, bootstrap_port):
        # Retry mechanism for connecting to the Bootstrap Server
        for attempt in range(self.max_retries):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.connect((bootstrap_host, bootstrap_port))
                    # Prepare the client information as JSON
                    client_info = {"name": self.name, "ip": self.host}
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

    def start_node_instance(self):
        # Logic to start a node.py instance
        print("Starting a node.py instance...")
        # For example, using subprocess to start a new Python script
        # subprocess.Popen(["python", "node.py"])
        pid = subprocess.Popen([sys.executable, "node.py"],
                               creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NEW_CONSOLE).pid

if __name__ == '__main__':
    # Create a control node instance with a unique name
    control_node = ControlNode(name="controlNode")
    # Connect the control node to the Bootstrap Server
    bootstrap_ip = open('bootstrap_ip.txt', 'r').read().strip()
    control_node.connect_to_bootstrap(bootstrap_ip, 50000)
