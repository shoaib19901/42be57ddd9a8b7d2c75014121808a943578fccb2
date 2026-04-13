import unittest
import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.proxy import ProxyServer

class TestSecurityFix(unittest.TestCase):
    def test_default_bind_address(self):
        proxy = ProxyServer()
        self.assertEqual(proxy.host, '127.0.0.1', "Default bind address should be 127.0.0.1 for security reasons.")

if __name__ == '__main__':
    unittest.main()
