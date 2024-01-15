import socket
import threading
import json
import hashlib
import time
import os


class BootstrapServer:
    def __init__(self, port=50000):
        self.host = open('bootstrap_ip.txt', 'r').read().strip()
        self.port = port
        self.auth_primary_node_ip = None  # Variable to store the authPrimary node IP
        self.auth_primary_node_port = None  # Variable to store the authPrimary port
        self.fdn_primary_node_ip = None  # Variable to store the fdnPrimary node
        self.fdn_primary_node_port = None   # Variable to store the fdnPrimary port
        self.nodes = {}
        self.client = None
        self.control_nodes = []  # List to store the control nodes
        self.control_node_ips = []  # List to store the control node IPs
        self.control_node_ports = []  # List to store the control node ports
        self.last_control_node_time = None  # Variable to store the time of the last control node registration

    def start_server(self):
        # Starts the server and listens for connections
        node_name = socket.gethostname()
        hostname, aliases, ip_addresses = socket.gethostbyname_ex(node_name)
        # Filter for IP addresses that start with 10 - for uni network machines
        ip_address_10 = next((ip for ip in ip_addresses if ip.startswith('10')), None)
        if ip_address_10:
            print(f"IP Address starting with '10': {ip_address_10}")
        else:
            print("No IP address starting with '10' found.")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((self.host, self.port))
            sock.listen()
            print(f"Bootstrap Server listening on {self.host}:{self.port}")

            while True:
                node, addr = sock.accept()
                threading.Thread(target=self.handle_connection, args=(node, addr)).start()

    def handle_connection(self, node, addr):
        # Handles a new connection
        try:
            data = node.recv(1024).decode('utf-8')
            node_info = json.loads(data)
            print(f"\nNODE INFO: {node_info}")

            # If the node is a control node add it to the control node list
            # If ten seconds have passed since the last control node registered, call startup
            if node_info['name'] == 'controlNode':
                self.control_nodes.append(node)
                self.control_node_ips.append(node_info['ip'])
                self.control_node_ports.append(node_info['port'])
                self.last_control_node_time = time.time()
                threading.Thread(target=self.check_startup).start()

            elif node_info['name'] == 'authPrimary':
                print(f"\nAuth Primary connected with info: {node_info}")
                print(f"Auth Primary connected from: {addr}\n")
                threading.Thread(target=self.handle_auth_primary, args=(node, node_info)).start()

            elif node_info['name'] == 'fdnPrimary':
                print(f"\nFdn Primary connected with info: {node_info}")
                print(f"Fdn Primary connected from: {addr}\n")
                threading.Thread(target=self.handle_fdn_primary, args=(node, node_info)).start()

            elif node_info['name'] == 'client':
                threading.Thread(target=self.handle_client, args=(node, node_info)).start()

        except Exception as e:
            print(f"Error: {e}")

    def check_startup(self):
        # Save the time of the last control node registration
        last_time = self.last_control_node_time
        # Wait for ten seconds
        time.sleep(10)
        # Check if no new control node has registered in the last ten seconds
        if last_time == self.last_control_node_time and len(self.control_nodes) >= 3:
            self.startup()

    def startup(self):
        # Start the authPrimary and fdnPrimary nodes
        num_control_nodes = len(self.control_nodes)

        if num_control_nodes == 0:
            print("No control nodes available to start node instances.")
            return

        auth_instruction = json.dumps({
                    "command": "start_PrimaryAuth",
                })
        self.control_nodes[0].sendall(auth_instruction.encode('utf-8'))
        print("Sent start_PrimaryAuth")

        time.sleep(1)
        fdn_instruction = json.dumps({
                    "command": "start_PrimaryFdn",
                })
        time.sleep(1)
        self.control_nodes[1].sendall(fdn_instruction.encode('utf-8'))
        print("Sent start_PrimaryFdn")

    def handle_auth_primary(self, sock, node_info):
        # Handle the authPrimary node

        # Store the authPrimary node IP and port
        self.auth_primary_node_ip = node_info['ip']
        self.auth_primary_node_port = node_info['port']

        # Send the control node list to the authPrimary node
        sock.sendall(b"Ready to provide controlNode list")
        print("Sent Ready to provide controlNode list message")
        auth_primary_message = sock.recv(1024).decode()
        print(f"Received authPrimary message: {auth_primary_message}")
        if auth_primary_message == "Send controlNode list":
            # Send the list of control node ips
            control_node_ips = json.dumps(self.control_node_ips)
            print(f"JSON control node ips: {control_node_ips}")
            sock.sendall(control_node_ips.encode())
            # Send the list of control node ports
            control_node_port_list = json.dumps(self.control_node_ports)
            print(f"JSON control node port list: {control_node_port_list}")
            sock.sendall(control_node_port_list.encode())

        auth_primary_message = sock.recv(1024).decode()

        if auth_primary_message == "Control Nodes Received":
            # Send the clientLogins.txt file to the authPrimary node
            file_path = "clientLogins.txt"
            with open(file_path, 'r') as file:
                file_content = file.read()

            print(f"File content to send: {file_content}")
            sock.sendall(file_content.encode('utf-8'))

            # Start the heartbeat thread
            handle_heartbeat_thread = threading.Thread(target=self.handle_heartbeat, args=(sock, node_info))
            handle_heartbeat_thread.daemon = True
            handle_heartbeat_thread.start()

    def handle_heartbeat(self, sock, node_info):
        # Handle the heartbeat from the authPrimary node and fdnPrimary node
        print(f"\n ** Receiving {node_info['name']} Heartbeats **")
        sock.sendall(b"Start heartbeat")
        while True:
            try:
                heartbeat_message = sock.recv(1024).decode()
                print(f"Heartbeat Received: {heartbeat_message}")
                if node_info['name'] == 'authPrimary':
                    # Write the contents of the heartbeat to the clientLogins.txt file
                    with open("clientLogins.txt", 'w') as file:
                        file.write(heartbeat_message)
                    print(f"\n** Updated clientLogins.txt file with new contents from {node_info['name']} **\n")
            except socket.error as e:
                print(f"Heartbeat failed - Error: {e}")
                primary_name = node_info['name']
                sock.close()
                # Generate a new primary node
                self.generate_new_primary(primary_name)
                break

    def generate_new_primary(self, primary_name):
        print(f"Primary {primary_name} failed. Generating new primary in 15 seconds...")
        for i in range(14, 0, -1):
            print(f"{i} seconds...")
            time.sleep(1)
        if primary_name == "authPrimary":
            auth_instruction = json.dumps({
                    "command": "start_PrimaryAuth",
                })
            self.control_nodes[0].sendall(auth_instruction.encode('utf-8'))
            print("Sent start_PrimaryAuth")
        elif primary_name == "fdnPrimary":
            fdn_instruction = json.dumps({
                    "command": "start_PrimaryFdn",
                })
            self.control_nodes[1].sendall(fdn_instruction.encode('utf-8'))
            print("Sent start_PrimaryFdn")

    def handle_fdn_primary(self, sock, node_info):
        # Handle the fdnPrimary node

        # Store the fdnPrimary node IP and port
        self.fdn_primary_node_ip = node_info['ip']
        self.fdn_primary_node_port = node_info['port']

        # Send the control node list to the fdnPrimary node
        sock.sendall(b"Ready to provide controlNode list")
        print("Sent Ready to provide controlNode list message")
        auth_primary_message = sock.recv(1024).decode()
        print(f"Received authPrimary message: {auth_primary_message}")
        if auth_primary_message == "Send controlNode list":
            # Send the list of control node ips
            control_node_ips = json.dumps(self.control_node_ips)
            print(f"JSON control node ips: {control_node_ips}")
            sock.sendall(control_node_ips.encode())
            # Send the list of control node ports
            control_node_port_list = json.dumps(self.control_node_ports)
            print(f"JSON control node port list: {control_node_port_list}")
            sock.sendall(control_node_port_list.encode())

        fdn_primary_message = sock.recv(1024).decode()

        if fdn_primary_message == "Control Nodes Received":
            # Send the list of audio files to the fdnPrimary node

            # Get list of all files in the 'audio_files' folder
            all_files = os.listdir('audio_files/using')

            # Filter out only audio files, assuming .mp3 extension
            audio_file_paths = [file for file in all_files if file.endswith('.mp3')]

            print(f"Audio file paths: {audio_file_paths}")

            # Send the number of files to expect
            number_of_files = len(audio_file_paths)
            print(f"Number of audio files to send: {number_of_files}")

            # Tell node how many files to expect
            sock.sendall(number_of_files.to_bytes(8, byteorder='big'))

            # Send the list of audio files to chose from
            audio_file_list = json.dumps(audio_file_paths)
            print(f"JSON audio file list: {audio_file_list}")
            print(f"JSON audio file list ENCODED: {audio_file_list.encode()}")
            sock.sendall(audio_file_list.encode())

            fdn_primary_message = sock.recv(1024).decode()
            if fdn_primary_message == "Ready to receive audio files":
                file_index = 0

                # Send the audio files to the fdnPrimary node
                while file_index < number_of_files:
                    print(audio_file_paths[file_index])
                    with open("audio_files/using/" + audio_file_paths[file_index], 'rb') as file:
                        mp3_file_content = file.read()
                        md5_hash = hashlib.md5(mp3_file_content).hexdigest()

                    sock.sendall(len(mp3_file_content).to_bytes(8, byteorder='big'))
                    print(f"Sent file size: {len(mp3_file_content)}")
                    sock.sendall(mp3_file_content)
                    sock.sendall(md5_hash.encode())

                    fdn_primary_message_2 = sock.recv(1024).decode()
                    if fdn_primary_message_2 == "File received":
                        print(f"fdnPrimary: File {file_index} received")
                        file_index += 1

            # Start the heartbeat thread
            handle_heartbeat_thread = threading.Thread(target=self.handle_heartbeat, args=(sock, node_info))
            handle_heartbeat_thread.daemon = True
            handle_heartbeat_thread.start()

    def handle_client(self, sock, node_info):
        # Handle the client node
        sock.sendall(b"Welcome client")

        print(f"Connected Client info: {node_info['ip'], node_info['port']}")

        message = sock.recv(1024).decode()
        print(f"Received message: {message}")

        if message == 'authPrimary address':
            # Send the authPrimary node IP and port to the client
            sock.sendall(self.auth_primary_node_ip.encode('utf-8'))
            print(f"Sent authPrimary address: {self.auth_primary_node_ip}")
            sock.sendall(self.auth_primary_node_port.to_bytes(8, byteorder='big'))
            print(f"Sent authPrimary port: {self.auth_primary_node_port}")

        elif message == 'fdnPrimary address':
            # Send the fdnPrimary node IP and port to the client
            sock.sendall(self.fdn_primary_node_ip.encode('utf-8'))
            print(f"Sent fdnPrimary address: {self.fdn_primary_node_ip}")
            sock.sendall(self.fdn_primary_node_port.to_bytes(8, byteorder='big'))
            print(f"Sent fdnPrimary port: {self.fdn_primary_node_port}")


if __name__ == '__main__':
    # Start the Bootstrap Server
    server = BootstrapServer()
    server.start_server()
