import socket

HOST = "127.0.0.1"
PORT = 65432

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
    client_socket.connect((HOST, PORT))  # Connect to server
    client_socket.sendall(b"Hello, server!")  # Send data
    data = client_socket.recv(1024)  # Receive response

print(f"Received from server: {data.decode()}")