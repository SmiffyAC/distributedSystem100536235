import socket
import threading
import json
import subprocess


# import psutil
# import netifaces as ni

class BootstrapServer:
    def __init__(self, port=50000):
        self.host = open('bootstrap_ip.txt', 'r').read().strip()
        self.port = port
        self.connected_nodes = []  # List to store socket objects of connected nodes
        self.auth_primary_node_ip = None  # Variable to store the authPrimary node IP
        self.auth_primary_node_port = None  # Variable to store the authPrimary port
        self.fdn_primary_node = None  # Variable to store the fdnPrimary node
        self.subAuthNodes = []  # List to store the subAuth nodes
        self.subFdnNodes = []  # List to store the subFdn nodes
        self.nodes = {}  # Dictionary to store registered nodes
        self.client = None

    def start_server(self):

        node_name = socket.gethostname()
        hostname, aliases, ip_addresses = socket.gethostbyname_ex(node_name)

        # Filter for IP addresses that start with '10'
        ip_address_10 = next((ip for ip in ip_addresses if ip.startswith('10')), None)

        if ip_address_10:
            print(f"IP Address starting with '10': {ip_address_10}")
        else:
            print("No IP address starting with '10' found.")

        # node_name = socket.gethostname()
        # node_ip = socket.gethostbyname_ex(node_name)
        # print(f"Node name: {node_ip}")
        #
        # bootstrap_info = socket.getaddrinfo(node_name, 50000)
        # print(f"Bootstrap info: {bootstrap_info}")

        # # Retrieve and print all IP addresses
        # ips = self.get_ip_addresses()
        # for interface, addresses in ips.items():
        #     print(f"Interface: {interface}, IPv4: {addresses['IPv4']}, IPv6: {addresses['IPv6']}")

        # # Retrieve and print all IP addresses
        # ips = self.get_ip_addresses()
        # for interface, addresses in ips.items():
        #     print(f"Interface: {interface}")
        #     print(f"  IPv4 addresses: {addresses['IPv4']}")
        #     print(f"  IPv6 addresses: {addresses['IPv6']}")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((self.host, self.port))
            sock.listen()
            print(f"Bootstrap Server listening on {self.host}:{self.port}")

            while True:
                node, addr = sock.accept()
                threading.Thread(target=self.handle_connection, args=(node, addr)).start()

    # def get_ip_addresses(self):
    #     ip_addresses = {}
    #     for interface in ni.interfaces():
    #         addresses = ni.ifaddresses(interface)
    #         # Get IPv4 addresses
    #         ipv4 = addresses.get(ni.AF_INET, [{}])[0].get('addr', 'No IPv4 Address')
    #         # Get IPv6 addresses
    #         ipv6 = addresses.get(ni.AF_INET6, [{}])[0].get('addr', 'No IPv6 Address')
    #         ip_addresses[interface] = {'IPv4': ipv4, 'IPv6': ipv6}
    #     return ip_addresses
    #

    # def get_ip_addresses(self):
    #     ip_addresses = {}
    #     for interface, addrs in psutil.net_if_addrs().items():
    #         ip_addresses[interface] = {'IPv4': [], 'IPv6': []}
    #         for addr in addrs:
    #             if addr.family == socket.AF_INET:
    #                 ip_addresses[interface]['IPv4'].append(addr.address)
    #             elif addr.family == socket.AF_INET6:
    #                 ip_addresses[interface]['IPv6'].append(addr.address)
    #     return ip_addresses

    def handle_connection(self, node, addr):
        try:
            data = node.recv(1024).decode('utf-8')
            node_info = json.loads(data)

            if node_info['name'] == 'node':
                print(f"\nNode connected with info: {node_info}")
                print(f"Node connected from: {addr}\n")
                self.handle_node(node, node_info, addr)

            elif node_info['name'] == 'authPrimary':
                print(f"\nAuth Primary connected with info: {node_info}")
                print(f"Auth Primary connected from: {addr}\n")
                self.handle_auth_primary(node, node_info)

            elif node_info['name'] == 'fdnPrimary':
                self.handle_fdn_primary(node, node_info)

            elif node_info['name'] == 'client':
                self.handle_client(node, node_info)

            elif node_info['name'] == 'authSub':
                print(f"\nSub Auth connected with info: {node_info}")
                print(f"Sub Auth connected from: {addr}\n")
                self.handle_sub_auth(node, node_info)

            elif node_info['name'] == 'fdnSub':
                self.handle_sub_fdn(node, node_info)

        except Exception as e:
            print(f"Error: {e}")

    def handle_node(self, node, node_info, addr):

        # connected_nodes[0] = authPrimary
        # connected_nodes[1] = authSub1
        # connected_nodes[2] = authSub2
        # connected_nodes[3] = fdnPrimary
        # connected_nodes[4] = fdnSub1
        # connected_nodes[5] = fdnSub2

        # Tell the first connected node to be authPrimary
        if len(self.connected_nodes) == 0:
            print("Length of connected nodes: ")
            print(len(self.connected_nodes))
            node.sendall(b"authPrimary")
            self.connected_nodes.append(node)  # Store the socket object
            print(f"Node handling authPrimary creation: {addr}")

        # Tell the second and third connected node to be AuthSub1 (TEMP)
        elif len(self.connected_nodes) == 1 or len(self.connected_nodes) == 2:
            node.sendall(b"subAuth")
            self.connected_nodes.append(node)


        # Tell the fourth connected node to be fdnPrimary (TEMP)
        elif len(self.connected_nodes) == 3:
            print("Length of connected nodes: ")
            print(len(self.connected_nodes))
            node.sendall(b"fdnPrimary")
            self.connected_nodes.append(node)  # Store the socket object
            print(f"Node handling fdnPrimary creation: {node_info['ip']}")

        # THE BELOW HAS BEEN COMMMENTED OUT SO I CAN TEST THE ABOVE ###############

        # elif len(self.connected_nodes) == 2 or len(self.connected_nodes) == 3:
        #     node.sendall(b"subAuth")
        #     self.connected_nodes.append(node)
        #
        # elif len(self.connected_nodes) == 4 or len(self.connected_nodes) == 5:
        #     node.sendall(b"subFdn")
        #     self.connected_nodes.append(node)

        ###########################################################################

    def handle_auth_primary(self, sock, node_info):

        self.auth_primary_node_ip = (node_info['ip'])
        self.auth_primary_node_port = (node_info['port'])
        print(f"SET Auth Primary Node IP: {self.auth_primary_node_ip}")
        print(f"SET Auth Primary Node Port: {self.auth_primary_node_port}")

        print(f"In handle_auth_primary")

        # Send JSON data
        # self.subAuthNodes.append('subAuth1')
        # self.subAuthNodes.append('subAuth2')

        # CURRENTLY ONLY HAVE 1 SUB AUTH
        print("Waiting for connected nodes to be 3 (waiting for subAuth1 and subAuth2)")
        while True:
            try:
                if len(self.subAuthNodes) == 2:
                    auth_nodes_json = json.dumps(self.subAuthNodes)
                    print(f"Auth Nodes JSON to send: {auth_nodes_json}")
                    sock.sendall(auth_nodes_json.encode('utf-8'))

                    file_path = "clientLogins.txt"
                    with open(file_path, 'r') as file:
                        file_content = file.read()

                    print(f"File content to send: {file_content}")
                    sock.sendall(file_content.encode('utf-8'))
                    break
            except:
                # Return to top of loop and try again
                pass

        # if len(self.connected_nodes) == 2:
        #     self.subAuthNodes.append(self.connected_nodes[2])



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

    def handle_sub_auth(self, sock, node_info):

        print(f"Connected subAuth info: {node_info['ip'], node_info['port']}")

        # Generate a name for the subAuth node based on the number of subAuth nodes
        authsub_name = "authSub" + str(len(self.subAuthNodes) + 1)

        self.subAuthNodes.append({"name": authsub_name, "ip": node_info['ip'], "port": node_info['port']})
        print(f"Sub Auth Nodes List: {self.subAuthNodes}")

        message = sock.recv(1024).decode()
        print(f"Received message: {message}")

        if message == 'authPrimary address':
            # print(f"Received message: {message}")
            sock.sendall(self.auth_primary_node_ip.encode('utf-8'))
            print(f"Sent authPrimary address: {self.auth_primary_node_ip}")
            sock.sendall(self.auth_primary_node_port.to_bytes(8, byteorder='big'))
            print(f"Sent authPrimary port: {self.auth_primary_node_port}")

    def handle_sub_fdn(self, sock, node_info):
        pass


if __name__ == '__main__':
    server = BootstrapServer()
    server.start_server()
