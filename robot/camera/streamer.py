"""Reusable MJPEG streamer. Call update() with a frame to push it to the stream."""

import cv2
import time
from threading import Lock, Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

BOUNDARY = b"--frameboundary"

HTML_PAGE = b"""\
<!DOCTYPE html>
<html>
<head><title>Stream</title></head>
<body style="margin:0;background:#111;display:flex;justify-content:center;align-items:center;height:100vh">
  <img src="/stream" style="max-width:100%;max-height:100vh">
</body>
</html>
"""


class MJPEGStreamer:
    def __init__(self, port=8080, quality=80):
        self.port = port
        self.quality = quality
        self._lock = Lock()
        self._jpeg: bytes = b""

    def start(self):
        """Start the HTTP server in a background thread."""
        streamer = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/stream":
                    self._stream()
                else:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(HTML_PAGE)

            def _stream(self):
                self.send_response(200)
                self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frameboundary")
                self.end_headers()
                try:
                    while True:
                        jpeg = streamer.get_jpeg()
                        if not jpeg:
                            time.sleep(0.01)
                            continue
                        self.wfile.write(BOUNDARY + b"\r\n")
                        self.wfile.write(b"Content-Type: image/jpeg\r\n")
                        self.wfile.write(f"Content-Length: {len(jpeg)}\r\n\r\n".encode())
                        self.wfile.write(jpeg)
                        self.wfile.write(b"\r\n")
                        time.sleep(0.033)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, fmt, *args):
                pass

        server = HTTPServer(("0.0.0.0", self.port), Handler)
        Thread(target=server.serve_forever, daemon=True).start()
        print(f"Streaming at http://localhost:{self.port}")

    def update(self, frame):
        """Push a new frame (BGR numpy array) to the stream."""
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, self.quality])
        with self._lock:
            self._jpeg = buf.tobytes()

    def get_jpeg(self) -> bytes:
        with self._lock:
            return self._jpeg