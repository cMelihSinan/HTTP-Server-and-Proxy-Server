import socket
import threading
import logging

# Setting up logging to help us debug and monitor the web server's behavior.
# INFO level is used to log important events like incoming connections and responses.
logging.basicConfig(level=logging.INFO, format='%(threadName)s: %(message)s')

class WebServer:
    def __init__(self, host='0.0.0.0', port=8080):
        # Initialize the server with the given host and port.
        self.host = host
        self.port = port

    def handle_client(self, client_socket):
        # Handle an incoming client connection.
        try:
            # Receive the HTTP request from the client.
            request = client_socket.recv(1024).decode('utf-8')
            logging.info(f"Request: {request}")

            # Parse the HTTP request.
            lines = request.splitlines()
            if not lines:
                return

            request_line = lines[0]
            method, uri, version = request_line.split()

            if method != "GET":
                # Respond with 501 Not Implemented if the method is not GET.
                client_socket.sendall(b"HTTP/1.1 501 Not Implemented\r\n\r\n")
                return

            try:
                # Extract the size from the URI and validate it.
                size = int(uri.lstrip('/'))
                if size < 100 or size > 20000:
                    # Respond with 400 Bad Request if the size is out of range.
                    client_socket.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\n")
                    return

                # Generate the response content.
                content = f"<HTML><BODY>{'a' * (size - 26)}</BODY></HTML>"
                response = (
                    f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: {len(content)}\r\n\r\n{content}"
                )
                # Send the response back to the client.
                client_socket.sendall(response.encode('utf-8'))
            except ValueError:
                # Respond with 400 Bad Request if the size is not a valid integer.
                client_socket.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\n")
        finally:
            # Close the client socket.
            client_socket.close()

    def start(self):
        # Start the web server and listen for incoming connections.
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)
        logging.info(f"Server running on {self.host}:{self.port}")

        try:
            while True:
                # Accept a client connection.
                client_socket, _ = server_socket.accept()
                # Handle the client connection in a separate thread.
                threading.Thread(target=self.handle_client, args=(client_socket,)).start()
        finally:
            # Close the server socket.
            server_socket.close()

if __name__ == "__main__":
    # Create and start the web server.
    WebServer().start()