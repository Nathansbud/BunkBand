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

KINECT_CF_INDEX = 0
KINECT_HZ = 100

sensor_queue = queue.Queue(maxsize=0)
kinect_queue = queue.Queue(maxsize=0)


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
        elif self.path.startswith("/kinect"):
            self.handle_kinect()
        else:
            self.respond(201, "idk what you did but i don't care")

    def handle_sensor(self):
        _, _, _sensor, _bucket = self.path.split("/")
        sensor_queue.put((int(_sensor), int(_bucket)))

        self.respond(200, "")

    def handle_kinect(self):
        if self.path.startswith("/kinect/exit"):
            handle_exit()
        else:
            queries = self.path.split("?")[1]
            queries_split = queries.split("&")

            x = float(queries_split[0].split("=")[1])
            y = float(queries_split[1].split("=")[1])

            print(f"Received kinect data: {x}, {y}")
            kinect_queue.put((x, y))

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

    get_kinect_height = lambda z: BASE_HEIGHT + 1.5 * z
    get_kinect_x = lambda x: 4 * x

    while not HAS_EXITED:
        sensor_msg = None
        kinect_msg = None

        try:
            sensor_msg = sensor_queue.get_nowait()
        except queue.Empty:
            # if we have no active available, simply ignore it and
            pass

        if sensor_msg:
            relevant_cf = crazyflies[sensor_msg[0]]
            relevant_cf.goTo(
                relevant_cf.initialPosition
                + np.array([0, 0, get_height(sensor_msg[1])]),
                0.0,
                1.0,
            )

        try:
            kinect_msg = kinect_queue.get_nowait()
        except queue.Empty:
            print("I am empty?")
            pass

        if kinect_msg:
            print(crazyflies)
            relevant_cf = crazyflies[KINECT_CF_INDEX]
            

            current_pos = relevant_cf.position()
            target_pos = relevant_cf.initialPosition + np.array(
                [get_kinect_x(kinect_msg[0]), 0, get_kinect_height(kinect_msg[1])]
            )

            distance_to_target = np.linalg.norm(target_pos - current_pos)
            max_speed = 1.5 # m/s

            max_distance = max_speed * (1 / KINECT_HZ)

            # it has 0.01 seconds to reach the target
            
            # if the distance is too far from us, we need to move it closer
            if distance_to_target > max_distance:
                vector_to_target = target_pos - current_pos
                unit_vector = vector_to_target / np.linalg.norm(vector_to_target)

                unit_vector *= max_distance
                target_pos = current_pos + unit_vector

        
            relevant_cf.goTo(
                target_pos,
                0.0,
                1 / KINECT_HZ,
            )

        if kinect_msg or sensor_msg:
            timeHelper.sleep(1 / KINECT_HZ)

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
