from http.server import BaseHTTPRequestHandler
import socketserver
import defines


class MyProxyServer(socketserver.ThreadingTCPServer):
    daemon_threads = False
    timeout = 5

    def __init__(self, address, port):
        return super().__init__((address, int(port)), MyProxyHandler)


class MyProxyHandler(BaseHTTPRequestHandler):
    timeout = 5
    buff = 8192

    def do_HEAD(self, **headers):
        self.send_response(200)
        [self.send_header(k, v) for k, v in headers.items()]
        self.end_headers()

    def do_GET(self):
        url = self.path[1:]
        if '://' in url:
            self.do_HEAD(**{'Content-type': 'application/octet-stream'})
            while not (defines.isCancel()):
                r = defines.request(url, trys=2, stream=True, timeout=self.timeout)
                for data in r.iter_content(self.buff):
                    self.wfile.write(data)
                    self.wfile.flush()

