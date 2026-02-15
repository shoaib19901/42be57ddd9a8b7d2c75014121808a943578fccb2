# Simple Python HTTP/HTTPS Proxy

This is a simple multi-threaded HTTP/HTTPS proxy server implemented in Python.

## Features

- Supports standard HTTP requests (GET, POST, etc.)
- Supports HTTPS tunneling via the `CONNECT` method
- Multi-threaded handling of concurrent connections

## Usage

### Running the Proxy

To start the proxy server, run:

```bash
python3 src/proxy.py
```

By default, the proxy listens on `0.0.0.0:8888`.

### Configuring Your Browser/System

Configure your browser or system to use the proxy server at `localhost` (or the server's IP) on port `8888`.

## Testing

To run the integration tests:

```bash
python3 tests/test_proxy.py
```
