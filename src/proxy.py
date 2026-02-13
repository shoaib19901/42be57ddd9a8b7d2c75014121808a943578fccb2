import socket
import threading
import select
from urllib.parse import urlparse

class ProxyServer:
    def __init__(self, host='0.0.0.0', port=8888):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def start(self):
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(100)
            print(f"[*] Proxy server listening on {self.host}:{self.port}")

            while True:
                client_socket, addr = self.server_socket.accept()
                print(f"[*] Accepted connection from {addr[0]}:{addr[1]}")
                client_handler = threading.Thread(target=self.handle_client, args=(client_socket,))
                client_handler.start()
        except Exception as e:
            print(f"[!] Error starting server: {e}")
        finally:
            self.server_socket.close()

    def handle_client(self, client_socket):
        try:
            request = client_socket.recv(4096)
            if not request:
                return

            first_line = request.split(b'\n')[0]
            url = first_line.split(b' ')[1]
            method = first_line.split(b' ')[0]

            if method == b'CONNECT':
                self.handle_https(client_socket, request, url)
            else:
                self.handle_http(client_socket, request, url)

        except Exception as e:
            print(f"[!] Error handling client: {e}")
            client_socket.close()

    def handle_https(self, client_socket, request, url):
        try:
            host_port = url.decode('utf-8')
            if ':' in host_port:
                host, port = host_port.split(':')
                port = int(port)
            else:
                host = host_port
                port = 443

            remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote_socket.connect((host, port))

            client_socket.send(b"HTTP/1.1 200 Connection Established\r\n\r\n")

            self.relay_data(client_socket, remote_socket)
        except Exception as e:
            print(f"[!] HTTPS Error: {e}")
            client_socket.close()

    def handle_http(self, client_socket, request, url):
        try:
            url_str = url.decode('utf-8')
            parsed = urlparse(url_str)

            scheme = parsed.scheme
            hostname = parsed.hostname
            port = parsed.port

            if not port:
                if scheme == 'https':
                    port = 443
                else:
                    port = 80

            if hostname:
                remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                remote_socket.connect((hostname, port))
                remote_socket.send(request)
                self.relay_data(client_socket, remote_socket)
            else:
                print(f"[!] Could not parse hostname from URL: {url_str}")
                client_socket.close()

        except Exception as e:
            print(f"[!] HTTP Error: {e}")
            client_socket.close()

    def relay_data(self, client, remote):
        try:
            while True:
                sockets = [client, remote]
                read_sockets, _, _ = select.select(sockets, [], [])

                if client in read_sockets:
                    data = client.recv(4096)
                    if not data:
                        break
                    remote.send(data)

                if remote in read_sockets:
                    data = remote.recv(4096)
                    if not data:
                        break
                    client.send(data)
        except Exception as e:
            pass # Connection closed
        finally:
            client.close()
            remote.close()

if __name__ == "__main__":
    proxy = ProxyServer()
    proxy.start()
