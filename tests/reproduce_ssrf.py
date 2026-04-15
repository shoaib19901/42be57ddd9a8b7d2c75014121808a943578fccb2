import unittest
import threading
import socket
import sys
import os
import time

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.proxy import ProxyServer

class SSRFReproductionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start a "secret" internal service on 127.0.0.1
        cls.secret_port = 7777
        cls.secret_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cls.secret_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            cls.secret_socket.bind(("127.0.0.1", cls.secret_port))
        except OSError:
            # Fallback if port is taken
            cls.secret_socket.bind(("127.0.0.1", 0))
            cls.secret_port = cls.secret_socket.getsockname()[1]

        cls.secret_socket.listen(5)

        def secret_service():
            while True:
                try:
                    conn, addr = cls.secret_socket.accept()
                    conn.recv(1024)
                    conn.send(b"HTTP/1.1 200 OK\r\nContent-Length: 11\r\n\r\nSecret Data")
                    conn.close()
                except:
                    break

        cls.secret_thread = threading.Thread(target=secret_service)
        cls.secret_thread.daemon = True
        cls.secret_thread.start()

        # Start proxy
        cls.proxy_port = 8877
        cls.proxy = ProxyServer(host="127.0.0.1", port=cls.proxy_port)
        cls.proxy_thread = threading.Thread(target=cls.proxy.start)
        cls.proxy_thread.daemon = True
        cls.proxy_thread.start()
        time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        cls.secret_socket.close()

    def test_ssrf_access_localhost(self):
        # Try to access the secret service through the proxy
        proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        proxy_socket.connect(("127.0.0.1", self.proxy_port))

        # Malicious request to internal service
        request = f"GET http://127.0.0.1:{self.secret_port}/ HTTP/1.1\r\nHost: 127.0.0.1:{self.secret_port}\r\nConnection: close\r\n\r\n"
        proxy_socket.send(request.encode())

        response = b""
        proxy_socket.settimeout(2)
        try:
            while True:
                data = proxy_socket.recv(4096)
                if not data:
                    break
                response += data
        except socket.timeout:
            pass
        proxy_socket.close()

        print(f"\nResponse from proxy: {response}")
        # If SSRF is fixed, we should NOT see the secret data
        self.assertNotIn(b"Secret Data", response, "SSRF vulnerability still exists: could access local service")
        self.assertEqual(response, b"", "Expected empty response from blocked connection")

if __name__ == "__main__":
    unittest.main()
