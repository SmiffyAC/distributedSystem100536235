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
        self.fdn_primary_node_port = None
        self.nodes = {}  # Dictionary to store registered nodes
        self.client = None
        self.control_nodes = []  # List to store the control nodes
        self.control_node_ips = []  # List to store the control node IPs
        self.control_node_ports = []  # List to store the control node ports
        self.last_control_node_time = None  # Variable to store the time of the last control node registration

    def start_server(self):
        node_name = socket.gethostname()
        hostname, aliases, ip_addresses = socket.gethostbyname_ex(node_name)
        # Filter for IP addresses that start with 10
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
        try:
            data = node.recv(1024).decode('utf-8')
            node_info = json.loads(data)
            print(f"\nNODE INFO: {node_info}")

            # If the node is a control node add it to the control node list
            #  if ten seconds have passed since the last control node registered, call startup
            if node_info['name'] == 'controlNode':
                self.control_nodes.append(node)
                self.control_node_ips.append(node_info['ip'])
                self.control_node_ports.append(node_info['port'])
                self.last_control_node_time = time.time()
                threading.Thread(target=self.check_startup).start()

            elif node_info['name'] == 'authPrimary':
                print(f"\nAuth Primary connected with info: {node_info}")
                print(f"Auth Primary connected from: {addr}\n")
                self.handle_auth_primary(node, node_info)

            elif node_info['name'] == 'fdnPrimary':
                print(f"\nFdn Primary connected with info: {node_info}")
                print(f"Fdn Primary connected from: {addr}\n")
                self.handle_fdn_primary(node, node_info)

            elif node_info['name'] == 'client':
                self.handle_client(node, node_info)

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
        #     instruct control nodes to start up 6 mod control nodes node instances
        #
        #     e.g. if we have 3 control nodes detected, we would tell 2 to start 3 nodes, and 1 to start 2 nodes
        #     ... then the rest of this code should work
        # Determine the number of node.py instances each control node should start
        # total_node_instances = 6
        num_control_nodes = len(self.control_nodes)

        if num_control_nodes == 0:
            print("No control nodes available to start node instances.")
            return

        # # Calculate the number of instances per control node
        # instances_per_node = total_node_instances // num_control_nodes
        # extra_instances = total_node_instances % num_control_nodes
        #
        # # print(f"Starting up {total_node_instances} node instances using {num_control_nodes} control nodes.")
        auth_instruction = json.dumps({
                    "command": "start_PrimaryAuth",
                })
        self.control_nodes[0].sendall(auth_instruction.encode('utf-8'))
        print("Sent start_PrimaryAuth")

        fdn_instruction = json.dumps({
                    "command": "start_PrimaryFdn",
                })
        time.sleep(1)
        self.control_nodes[1].sendall(fdn_instruction.encode('utf-8'))
        print("Sent start_PrimaryFdn")

    def handle_auth_primary(self, sock, node_info):

        self.auth_primary_node_ip = node_info['ip']
        self.auth_primary_node_port = node_info['port']

        sock.sendall(b"Ready to provide controlNode list")
        print("Sent Ready to provide controlNode list message")
        # Send the list of control node ips
        control_node_ips = json.dumps(self.control_node_ips)
        print(f"JSON control node ips: {control_node_ips}")
        sock.sendall(control_node_ips.encode())
        # Send the list of control node ports
        control_node_port_list = json.dumps(self.control_node_ports)
        print(f"JSON control node port list: {control_node_port_list}")
        sock.sendall(control_node_port_list.encode())

        file_path = "clientLogins.txt"
        with open(file_path, 'r') as file:
            file_content = file.read()

        print(f"File content to send: {file_content}")
        sock.sendall(file_content.encode('utf-8'))

        handle_heartbeat_thread = threading.Thread(target=self.handle_heartbeat, args=(sock, node_info))
        handle_heartbeat_thread.daemon = True
        handle_heartbeat_thread.start()
        # self.handle_heartbeat(sock)

        # ADD STUFF ABOUT HEARTBEAT FOR KILLING NODES

    def handle_heartbeat(self, sock, node_info):
        print(f"\n ** Receiving {node_info['name']} Heartbeats **")
        sock.sendall(b"Start heartbeat")
        # Set a timeout for the socket
        # sock.settimeout(30)
        while True:
            primary_name = None
            try:
                heartbeat_message = sock.recv(1024).decode()
                print(f"Heartbeat Received: {heartbeat_message}")
                json_heartbeat = json.loads(heartbeat_message)
                # Get the ip and port of the fdnSub that sent the heartbeat
                primary_name = json_heartbeat[0]
                primary_ip = json_heartbeat[1]
                primary_port = json_heartbeat[2]
                primary_num_of_subs = json_heartbeat[3]
            # except socket.timeout:
            #     print("Heartbeat timed out")
            #     primary_name = node_info['name']
            #     self.generate_new_primary(primary_name)
            except socket.error as e:
                print(f"Heartbeat failed - Error: {e}")
                primary_name = node_info['name']
                sock.close()
                self.generate_new_primary(primary_name)
                break

    def generate_new_primary(self, primary_name):
        print(f"Primary {primary_name} failed. Generating new primary in 15 seconds...")
        # time.sleep(15)
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

        self.fdn_primary_node_ip = node_info['ip']
        self.fdn_primary_node_port = node_info['port']

        sock.sendall(b"Ready to provide controlNode list")
        print("Sent Ready to provide controlNode list message")
        # Send the list of control node ips
        control_node_ips = json.dumps(self.control_node_ips)
        print(f"JSON control node ips: {control_node_ips}")
        sock.sendall(control_node_ips.encode())
        # Send the list of control node ports
        control_node_port_list = json.dumps(self.control_node_ports)
        print(f"JSON control node port list: {control_node_port_list}")
        sock.sendall(control_node_port_list.encode())

        # ADD STUFF FOR SENDING THE AUDIO FILES

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

            # fdn_primary_message_3 = sock.recv(1024).decode()
            #
            # if fdn_primary_message_3 == "All files Received":
            #     sock.sendall(b"Ready to provide fdnPrimary address")
            #
            #     message = sock.recv(1024).decode()
            #     print(f"Received message: {message}")
            #
            #     if message == 'fdnPrimary address':
            #         # print(f"Received message: {message}")
            #         sock.sendall(self.fdn_primary_node_ip.encode('utf-8'))
            #         print(f"Sent fdnPrimary address: {self.fdn_primary_node_ip}")
            #         sock.sendall(self.fdn_primary_node_port.to_bytes(8, byteorder='big'))
            #         print(f"Sent fdnPrimary port: {self.fdn_primary_node_port}")

        # sock.sendall(b"Start heartbeat")
        handle_heartbeat_thread = threading.Thread(target=self.handle_heartbeat, args=(sock, node_info))
        handle_heartbeat_thread.daemon = True
        handle_heartbeat_thread.start()

        # self.handle_heartbeat(sock)

        # ADD STUFF ABOUT HEARTBEAT FOR KILLING NODES

    def handle_client(self, sock, node_info):
        sock.sendall(b"Welcome client")

        print(f"Connected Client info: {node_info['ip'], node_info['port']}")

        message = sock.recv(1024).decode()
        print(f"Received message: {message}")

        if message == 'authPrimary address':
            # print(f"Received message: {message}")
            sock.sendall(self.auth_primary_node_ip.encode('utf-8'))
            print(f"Sent authPrimary address: {self.auth_primary_node_ip}")
            sock.sendall(self.auth_primary_node_port.to_bytes(8, byteorder='big'))
            print(f"Sent authPrimary port: {self.auth_primary_node_port}")

        elif message == 'fdnPrimary address':
            # print(f"Received message: {message}")
            sock.sendall(self.fdn_primary_node_ip.encode('utf-8'))
            print(f"Sent fdnPrimary address: {self.fdn_primary_node_ip}")
            sock.sendall(self.fdn_primary_node_port.to_bytes(8, byteorder='big'))
            print(f"Sent fdnPrimary port: {self.fdn_primary_node_port}")


if __name__ == '__main__':
    server = BootstrapServer()
    server.start_server()
