import unittest
import threading
import time
import socket
import urllib.request
import sys
import os
import http.server
import socketserver

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.proxy import ProxyServer

class MockHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Hello World")

    def log_message(self, format, *args):
        pass # Suppress logging

class TestProxyServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start mock server in a separate thread
        cls.server_port = 9999
        cls.httpd = socketserver.TCPServer(("127.0.0.1", cls.server_port), MockHandler)
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()

        # Start proxy in a separate thread
        cls.proxy_port = 8899
        cls.proxy = ProxyServer(port=cls.proxy_port)
        cls.proxy_thread = threading.Thread(target=cls.proxy.start)
        cls.proxy_thread.daemon = True
        cls.proxy_thread.start()
        time.sleep(1) # Give them a second to start

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def test_http_proxy(self):
        proxy_url = f"http://127.0.0.1:{self.proxy_port}"
        proxy_handler = urllib.request.ProxyHandler({'http': proxy_url})
        opener = urllib.request.build_opener(proxy_handler)

        target_url = f"http://127.0.0.1:{self.server_port}/"

        try:
            response = opener.open(target_url)
            self.assertEqual(response.status, 200)
            content = response.read()
            self.assertEqual(content, b"Hello World")
        except Exception as e:
            self.fail(f"HTTP Proxy test failed: {e}")

    def test_unparseable_hostname(self):
        # Sending a request with a relative path instead of an absolute URL
        # This should cause urlparse to not find a hostname
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(('127.0.0.1', self.proxy_port))
        s.send(b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n")
        data = s.recv(4096)
        self.assertEqual(data, b"", "Proxy should close the connection when hostname cannot be parsed")
        s.close()

if __name__ == '__main__':
    unittest.main()
