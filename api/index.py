from http.server import BaseHTTPRequestHandler
import requests

PDF_URL = "https://fir.bsu.by/images/timetable/ILOG_timetable.pdf"

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            res = requests.get(PDF_URL, timeout=10)
            res.raise_for_status()

            self.send_response(200)
            self.send_header('Content-type', 'application/pdf')
            self.end_headers()
            self.wfile.write(res.content)
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(str(e).encode())
