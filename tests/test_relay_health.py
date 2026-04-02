import unittest
from unittest.mock import Mock, patch
import socket
import sys
import io

# Add the src directory to the path to import ProxyServer
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.proxy import ProxyServer

class TestRelayHealth(unittest.TestCase):
    def setUp(self):
        self.proxy = ProxyServer()
        self.mock_client = Mock()
        self.mock_remote = Mock()

    @patch('select.select')
    def test_relay_unexpected_exception_logged(self, mock_select):
        # Simulate an unexpected exception in select.select
        mock_select.side_effect = RuntimeError("Unexpected failure")

        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            self.proxy.relay_data(self.mock_client, self.mock_remote)
        finally:
            sys.stdout = sys.__stdout__

        output = captured_output.getvalue()
        self.assertIn("[!] Relay error: Unexpected failure", output)
        self.mock_client.close.assert_called_once()
        self.mock_remote.close.assert_called_once()

    @patch('select.select')
    def test_relay_expected_exception_not_logged(self, mock_select):
        # Simulate an expected exception in select.select
        mock_select.side_effect = ConnectionResetError("Connection reset by peer")

        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            self.proxy.relay_data(self.mock_client, self.mock_remote)
        finally:
            sys.stdout = sys.__stdout__

        output = captured_output.getvalue()
        self.assertNotIn("[!] Relay error:", output)
        self.mock_client.close.assert_called_once()
        self.mock_remote.close.assert_called_once()

    @patch('select.select')
    def test_relay_broken_pipe_not_logged(self, mock_select):
        # Simulate another expected exception in select.select
        mock_select.side_effect = BrokenPipeError("Broken pipe")

        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            self.proxy.relay_data(self.mock_client, self.mock_remote)
        finally:
            sys.stdout = sys.__stdout__

        output = captured_output.getvalue()
        self.assertNotIn("[!] Relay error:", output)
        self.mock_client.close.assert_called_once()
        self.mock_remote.close.assert_called_once()

if __name__ == '__main__':
    unittest.main()
