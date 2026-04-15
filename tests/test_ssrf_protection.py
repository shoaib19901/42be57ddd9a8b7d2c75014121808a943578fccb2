import unittest
import socket
import sys
import os
from unittest.mock import MagicMock, patch

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.proxy import ProxyServer

class TestSSRFProtection(unittest.TestCase):
    def setUp(self):
        if 'PROXY_ALLOW_INTERNAL' in os.environ:
            del os.environ['PROXY_ALLOW_INTERNAL']
        self.proxy = ProxyServer()

    def test_get_safe_ip_loopback(self):
        self.assertIsNone(self.proxy.get_safe_ip('127.0.0.1'))
        self.assertIsNone(self.proxy.get_safe_ip('localhost'))
        try:
            self.assertIsNone(self.proxy.get_safe_ip('::1', family=socket.AF_INET6))
        except socket.gaierror:
            # IPv6 might not be supported in this environment
            pass

    def test_get_safe_ip_private(self):
        self.assertIsNone(self.proxy.get_safe_ip('10.0.0.1'))
        self.assertIsNone(self.proxy.get_safe_ip('172.16.0.1'))
        self.assertIsNone(self.proxy.get_safe_ip('192.168.1.1'))

    def test_get_safe_ip_public(self):
        # We need to mock socket.getaddrinfo to avoid actual DNS resolution in some environments
        # but for common public IPs it should be fine.
        # Let's mock it to be sure.
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 0))]
            self.assertEqual(self.proxy.get_safe_ip('example.com'), '93.184.216.34')

    def test_get_safe_ip_malicious_dns(self):
        # Test a hostname that resolves to a private IP
        with patch('socket.getaddrinfo') as mock_getaddrinfo:
            mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('10.0.0.1', 0))]
            self.assertIsNone(self.proxy.get_safe_ip('evil.internal'))

    @patch('src.proxy.ProxyServer.get_safe_ip')
    def test_handle_http_blocks_unsafe(self, mock_get_ip):
        mock_get_ip.return_value = None
        client_socket = MagicMock()
        url = b'http://127.0.0.1/'
        request = b'GET http://127.0.0.1/ HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n'

        self.proxy.handle_http(client_socket, request, url)

        client_socket.close.assert_called()

    @patch('src.proxy.ProxyServer.get_safe_ip')
    def test_handle_https_blocks_unsafe(self, mock_get_ip):
        mock_get_ip.return_value = None
        client_socket = MagicMock()
        url = b'127.0.0.1:443'
        request = b'CONNECT 127.0.0.1:443 HTTP/1.1\r\n\r\n'

        self.proxy.handle_https(client_socket, request, url)

        client_socket.close.assert_called()

if __name__ == '__main__':
    unittest.main()
