import socket
import threading
import select
import ipaddress
import os
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

    def get_safe_ip(self, host, family=socket.AF_INET):
        if os.environ.get('PROXY_ALLOW_INTERNAL') == 'true':
            try:
                ip_info = socket.getaddrinfo(host, None, family=family)
                if ip_info:
                    return ip_info[0][4][0]
            except Exception:
                pass
            return None

        try:
            # Resolve the hostname to all its IP addresses for the given family
            ip_info = socket.getaddrinfo(host, None, family=family)
            if not ip_info:
                return None

            # To prevent DNS rebinding, we must validate all resolved IPs
            # and then use one of the validated IPs for the connection.
            for item in ip_info:
                ip_str = item[4][0]
                ip = ipaddress.ip_address(ip_str)
                if ip.is_loopback or ip.is_private or ip.is_link_local:
                    return None

            # If all resolved IPs are safe, return the first one
            return ip_info[0][4][0]
        except Exception as e:
            print(f"[!] Host validation error for {host}: {e}")
            return None

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
        remote_socket = None
        try:
            host_port = url.decode('utf-8')
            # Handle IPv6 addresses in CONNECT requests [2001:db8::1]:443
            if host_port.startswith('['):
                end_bracket = host_port.find(']')
                if end_bracket != -1:
                    host = host_port[1:end_bracket]
                    remaining = host_port[end_bracket+1:]
                    if remaining.startswith(':'):
                        port = int(remaining[1:])
                    else:
                        port = 443
                    family = socket.AF_INET6
                else:
                    # Malformed IPv6
                    client_socket.close()
                    return
            elif ':' in host_port:
                host, port = host_port.split(':')
                port = int(port)
                family = socket.AF_INET
            else:
                host = host_port
                port = 443
                family = socket.AF_INET

            safe_ip = self.get_safe_ip(host, family=family)
            if not safe_ip:
                print(f"[!] Blocked unsafe or unresolvable HTTPS connection to: {host}")
                client_socket.close()
                return

            remote_socket = socket.socket(family, socket.SOCK_STREAM)
            remote_socket.connect((safe_ip, port))

            client_socket.send(b"HTTP/1.1 200 Connection Established\r\n\r\n")

            self.relay_data(client_socket, remote_socket)
        except Exception as e:
            print(f"[!] HTTPS Error: {e}")
            if remote_socket:
                remote_socket.close()
            client_socket.close()

    def handle_http(self, client_socket, request, url):
        remote_socket = None
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
                # HTTP often uses IPv4, but let's try to be flexible if the hostname is an IPv6 literal
                family = socket.AF_INET
                if hostname.startswith('[') and hostname.endswith(']'):
                    hostname = hostname[1:-1]
                    family = socket.AF_INET6

                safe_ip = self.get_safe_ip(hostname, family=family)
                if not safe_ip:
                    print(f"[!] Blocked unsafe or unresolvable HTTP connection to: {hostname}")
                    client_socket.close()
                    return

                remote_socket = socket.socket(family, socket.SOCK_STREAM)
                remote_socket.connect((safe_ip, port))
                remote_socket.send(request)
                self.relay_data(client_socket, remote_socket)
            else:
                print(f"[!] Could not parse hostname from URL: {url_str}")
                client_socket.close()

        except Exception as e:
            print(f"[!] HTTP Error: {e}")
            if remote_socket:
                remote_socket.close()
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
