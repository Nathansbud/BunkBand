import queue
import signal
import sys
import threading
import time

import numpy as np

from crazyflie_py import Crazyswarm
from http.server import HTTPServer, SimpleHTTPRequestHandler

HAS_EXITED = False
SURPRESS_SYSTEM_LOGS = True
DIRECTORY = "."

msg_queue = queue.Queue(maxsize=0)


class RequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def log_message(self, format: str, *args) -> None:
        if SURPRESS_SYSTEM_LOGS:
            return

        return super().log_message(format, *args)

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
    BASE_HEIGHT = 0.5

    swarm = Crazyswarm()
    timeHelper = swarm.timeHelper
    allcfs = swarm.allcfs

    crazyflies = allcfs.crazyflies

    # Take off all the crazyflies
    for cf in crazyflies:
        cf.takeoff(targetHeight=BASE_HEIGHT, duration=1.0)

    timeHelper.sleep(1.0)

    get_height = lambda bucket: BASE_HEIGHT + 0.25 * bucket

    while not HAS_EXITED:
        msg = None

        try:
            msg = msg_queue.get_nowait()
        except queue.Empty:
            # if we have no active available, simply ignore it and
            pass

        if msg:
            relevant_cf = crazyflies[msg[0]]
            relevant_cf.goTo(
                relevant_cf.initialPosition + np.array([0, 0, get_height(msg[1])]),
                0.0,
                1.0,
            )

            timeHelper.sleep(1)

    # if we have received an exit, land all cfs
    for cf in crazyflies:
        cf.land(0.04, 2.0)

    timeHelper.sleep(2.0)


def handle_exit():
    global HAS_EXITED
    HAS_EXITED = True

    t1.join()
    sys.exit(0)


if __name__ == "__main__":
    t1 = threading.Thread(target=test_flight_loop)
    t2 = threading.Thread(target=command_receiver)

    t1.start()
    t2.start()

    # Attempt to land gracefully if a SIGTERM/SIGINT is triggered
    # for s in [signal.SIGTERM, signal.SIGINT]:
    #     signal.signal(s, lambda a, b: handle_exit())