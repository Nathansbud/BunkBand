from http.server import HTTPServer, SimpleHTTPRequestHandler
import serial

DIRECTORY = "."
path = "/dev/cu.usbmodem101"
arduino = serial.Serial(path, 9600)

class RequestHandler(SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        if self.path.startswith("/tempo/"):
            self.handle_tempo()
        else:
            self.respond(201, "idk what you did but i don't care")


    def respond(self, status, content=None):
        c = (content if content else "").encode("utf-8")
        c_len = len(c)

        self.send_response(status)
        self.send_header("Content-Type", "text/plain")

        if c_len:
            self.send_header("Content-Length", c_len)

        self.end_headers()
        if c_len:
            self.wfile.write(c)

    def handle_tempo(self):
        _, _, tempo = self.path.split("/")
        print("tempo:" , tempo)
        arduino.write(tempo.strip().encode("utf-8"))
        self.respond(200, "")

with HTTPServer(("0.0.0.0", 7001), RequestHandler) as httpd:
    httpd.serve_forever()
