#  I NEED TO CONNECT BACK TO THE NODE THAT JUST CREATED ME USING THE IP AND PORT PASSED TO ME.
#  THEN ONCE A CONNECTION HAS BEEN MADE I NEED TO LISTEN TO RECEIVE SOMETHING.

import socket
import sys


def main(node_ip, node_port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((node_ip, node_port))
        # Ready to receive data
        print("Connected to node at " + node_ip + ":" + str(node_port))
        # response = s.recv(1024).decode()
        # print("Received response: " + response)
        # while True:
        #     data = s.recv(1024)
        #     if data:
        #         # Process received data
        #         print("Received:", data.decode())
        #         # Send response

        while True:
            s.sendall(b"authPrimary process has been created")

            client_list_data = s.recv(1024).decode()
            print(f"Received list data: {client_list_data}")

            client_file_data = s.recv(1024).decode()
            print(f"Received file data: {client_file_data}")

            s.sendall(b"I have received the data")


if __name__ == '__main__':
    # if len(sys.argv) != 3:
    #     print("Usage: python authPrimary.py <Node IP> <Node Port>")
    #     sys.exit(1)

    main(sys.argv[1], int(sys.argv[2]))

# ... [rest of the authPrimary.py script] ...
