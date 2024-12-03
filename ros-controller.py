import threading
import queue

import numpy as np
from crazyflie_py import Crazyswarm

from http.server import HTTPServer, SimpleHTTPRequestHandler

DIRECTORY = "."
msg_queue = queue.Queue(maxsize=0)

class RequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        if self.path.startswith("/sensor/"):
            self.handle_sensor()
        else:
            self.respond(201, "idk what you did but i don't care")

    def handle_sensor(self):
        _, _, _sensor, _bucket = self.path.split("/")
        msg_queue.put((int(_sensor), int(_bucket)))

        self.respond(200, "")

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


def command_receiver():
    with HTTPServer(("0.0.0.0", 7001), RequestHandler) as httpd:
        httpd.serve_forever()


def test_flight_loop():
    Z = 1.0

    swarm = Crazyswarm()
    timeHelper = swarm.timeHelper
    allcfs = swarm.allcfs

    crazyflies = allcfs.crazyflies

    # Take off all the crazyflies
    for cf in crazyflies:
        cf.takeoff(targetHeight=Z, duration=1.0)

    timeHelper.sleep(1.0)

    for i in range(3):
        for i in range(5):
            # Z/2 to scale the received value to fit the lab
            Z = 1.0 + (0.3125 * i)

            duration = 1.0
            for cf in allcfs.crazyflies:
                pos = np.array(cf.initialPosition) + np.array([0, 0, Z])
                cf.goTo(pos, 0.0, duration)

            # does this pause the loop or just the drone ?
            timeHelper.sleep(duration)

    for cf in crazyflies:
        cf.land(0.04, 2.0)

    timeHelper.sleep(2.0)
    pass


if __name__ == "__main__":
    # t1 = threading.Thread(target=test_flight_loop)
    t2 = threading.Thread(target=command_receiver)
    t2.start()
