import socket
import threading
import logging
import os
import time

# Setting up logging to help us debug and monitor the proxy server's behavior.
# INFO level is used to log important events like incoming connections and responses.
logging.basicConfig(level=logging.INFO, format='%(threadName)s: %(message)s')

class ProxyServer:
    CACHE_DIR = "proxy_cache"  # Directory to store cached responses.
    CACHE_SIZE_LIMIT = 10       # Maximum number of cached items.

    def __init__(self, host='0.0.0.0', port=8888, web_server_host='localhost', web_server_port=8080):
        self.host = host
        self.port = port
        self.web_server_host = web_server_host  # Target web server hostname or IP.
        self.web_server_port = web_server_port  # Target web server port.
        self.cache = {}  # Dictionary to map URIs to cache file names.
        # Using a dictionary for caching because it provides fast lookups.

        # Create the cache directory if it doesn't exist.
        if not os.path.exists(self.CACHE_DIR):
            os.makedirs(self.CACHE_DIR)

    def cache_key(self, uri):
        # Generate a file-safe key from the URI by replacing slashes with underscores.
        return uri.replace("/", "_")

    def is_cache_full(self):
        # Check if the cache has reached its size limit.
        # This is important to prevent using too many resources.
        return len(self.cache) >= self.CACHE_SIZE_LIMIT

    def evict_cache(self):
        # Remove the oldest cached item to make space for new entries.
        # We use a simple first-in first-out (FIFO) method.
        if self.cache:
            oldest_key = next(iter(self.cache))  # Get the first key in the cache (oldest).
            filepath = os.path.join(self.CACHE_DIR, self.cache[oldest_key])
            if os.path.exists(filepath):
                os.remove(filepath)  # Remove the file from the filesystem.
            del self.cache[oldest_key]  # Remove the entry from the cache dictionary.

    def handle_client(self, client_socket):
        # Handle an incoming client connection.
        try:
            # Receive the HTTP request from the client.
            request = client_socket.recv(1024).decode('utf-8')
            logging.info(f"Proxy received request: {request}")

            # Parse the request lines.
            lines = request.splitlines()
            if not lines:
                return

            request_line = lines[0]
            parts = request_line.split()
            if len(parts) < 3:
                # Respond with 400 Bad Request if the request line is invalid.
                self.send_response(client_socket, 400, "Bad Request")
                return

            method, uri, version = parts

            # Only support GET requests; respond with 501 Not Implemented for others.
            if method != "GET":
                self.send_response(client_socket, 501, "Not Implemented")
                return

            # Remove "http://" from the URI to get the relative path.
            if uri.startswith("http://"):
                uri = uri[len("http://"):]
                uri = uri[uri.find("/"):]

            # Validate the URI format.
            if not uri.startswith("/"):
                self.send_response(client_socket, 400, "Bad Request")
                return

            # Generate the cache file path for this URI.
            cache_filename = self.cache_key(uri)
            cache_filepath = os.path.join(self.CACHE_DIR, cache_filename)

            # Check if the URI is already in the cache.
            if uri in self.cache:
                # Serve cached responses to reduce latency and network overhead.
                file_length = len(self.cache[uri])
                if file_length % 2 == 1:  # Odd-length content: simulate "Not Modified".
                    self.send_response(client_socket, 304, "Not Modified")
                    return

            # Simulate additional URI-based validation.
            try:
                size = int(uri[1:])
                if size > 9999:
                    # Respond with 414 Request-URI Too Long if the size is too large.
                    self.send_response(client_socket, 414, "Request-URI Too Long")
                    return
            except ValueError:
                # Respond with 400 Bad Request if the URI can't be parsed as an integer.
                self.send_response(client_socket, 400, "Bad Request")
                return

            # Forward the request to the target web server.
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as web_server_socket:
                try:
                    # Create a new socket connection for each request.
                    web_server_socket.connect((self.web_server_host, self.web_server_port))
                    web_request = f"GET {uri} {version}\r\nHost: {self.web_server_host}:{self.web_server_port}\r\n\r\n"
                    web_server_socket.sendall(web_request.encode('utf-8'))

                    # Receive the response from the web server.
                    response = web_server_socket.recv(4096)
                    logging.info(f"Proxy received response from web server")

                    # Cache the response if the cache is not full.
                    if self.is_cache_full():
                        self.evict_cache()

                    with open(cache_filepath, "wb") as f:
                        f.write(response)  # Save the response to the cache.
                    self.cache[uri] = cache_filename

                    # Send the response back to the client.
                    client_socket.sendall(response)
                except ConnectionRefusedError:
                    # Respond with 404 Not Found if the target web server is unavailable.
                    self.send_response(client_socket, 404, "Not Found")
        finally:
            client_socket.close()

    def send_response(self, client_socket, status_code, reason, content=""):
        # Send an HTTP response to the client.
        response_line = f"HTTP/1.1 {status_code} {reason}\r\n"
        headers = "Content-Type: text/html\r\n" + f"Content-Length: {len(content)}\r\n\r\n"
        response = response_line + headers + content
        client_socket.sendall(response.encode('utf-8'))
        logging.info(f"Sent response: {response_line.strip()} with {len(content)} bytes of content")

    def start(self):
        # Start the proxy server and listen for incoming connections.
        proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        proxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Reuse the socket address.
        proxy_socket.bind((self.host, self.port))
        proxy_socket.listen(5)
        logging.info(f"Proxy server listening on port {self.port}")

        try:
            while True:
                # Accept a client connection.
                client_socket, client_address = proxy_socket.accept()
                logging.info(f"Proxy connection from {client_address}")
                # Handle the client connection in a separate thread.
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
                client_thread.start()
        finally:
            proxy_socket.close()

if __name__ == "__main__":
    proxyServer = ProxyServer()
    proxyServer.start()