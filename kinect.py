# coding: utf-8

import time
import numpy as np
import cv2
import sys
from pylibfreenect2 import Freenect2, SyncMultiFrameListener
from pylibfreenect2 import FrameType, Registration, Frame
from pylibfreenect2 import createConsoleLogger, setGlobalLogger
from pylibfreenect2 import LoggerLevel

# ------------------------------- SETUP KINECT --------------------------------------- 

try:
    from pylibfreenect2 import OpenGLPacketPipeline
    pipeline = OpenGLPacketPipeline()
except:
    try:
        from pylibfreenect2 import OpenCLPacketPipeline
        pipeline = OpenCLPacketPipeline()
    except:
        from pylibfreenect2 import CpuPacketPipeline
        pipeline = CpuPacketPipeline()
print("Packet pipeline:", type(pipeline).__name__)

# Create and set logger
logger = createConsoleLogger(LoggerLevel.Debug)
setGlobalLogger(logger)

fn = Freenect2()
num_devices = fn.enumerateDevices()
if num_devices == 0:
    print("No device connected!")
    sys.exit(1)

serial = fn.getDeviceSerialNumber(0)
device = fn.openDevice(serial, pipeline=pipeline)

listener = SyncMultiFrameListener(
    FrameType.Color | FrameType.Ir | FrameType.Depth)

# Register listeners
device.setColorFrameListener(listener)
device.setIrAndDepthFrameListener(listener)

device.start()

# NOTE: must be called after device.start()
registration = Registration(device.getIrCameraParams(),
                            device.getColorCameraParams())

undistorted = Frame(512, 424, 4)
registered = Frame(512, 424, 4)

# Optinal parameters for registration
# set True if you need
need_bigdepth = False
need_color_depth_map = False

bigdepth = Frame(1920, 1082, 4) if need_bigdepth else None
color_depth_map = np.zeros((424, 512),  np.int32).ravel() \
    if need_color_depth_map else None

# ----------------------------- END SETUP KINECT -------------------------------------

# ------------------------------- SETUP COMMS ----------------------------------------

USING_ROS = True
USING_MAX = True

from pythonosc.udp_client import SimpleUDPClient
import requests

ROS_IP = "138.16.161.225"
MAX_IP = "138.16.161.129"

MAX_PORT = 6813
ROS_PORT = 7001

max_client = SimpleUDPClient(MAX_IP, MAX_PORT)

def send_to_max(x, y):
    max_client.send_message(f"/kinect", (x, y))

def send_to_ros(x, y):
    print(f"Sending to ROS: {x}, {y}")
    _ = requests.get(
        f"http://{ROS_IP}:{ROS_PORT}/kinect?x={x}&y={y}"
    )

# ----------------------------- END SETUP COMMS --------------------------------------

# ------------------------------- KINECT FUNCTIONS -----------------------------------

def limit_depth(depth, min_d=0, max_d=4500) -> np.ndarray:
    depth_copy = np.copy(depth)

    # any depth value outside the range [min_d, max_d] is set to 0
    pixels_in_range = np.logical_and(min_d < depth_copy, depth_copy < max_d)
    depth_copy[~pixels_in_range] = 0
    
    return depth_copy

def find_average_center(depth_map: np.ndarray) -> tuple:
    # depth_map is a 2D numpy array
    # returns the average of the x and y coordinates of the pixels in the depth_map
    # that are not 0
    x_sum = 0
    y_sum = 0
    num_pixels = 0
    for i in range(depth_map.shape[0]):
        for j in range(depth_map.shape[1]):
            if depth_map[i][j] != 0:
                x_sum += j
                y_sum += i
                num_pixels += 1
    if num_pixels == 0:
        return (0, 0)
    return (x_sum / num_pixels, y_sum / num_pixels)


callibration_step = 0
last_step_start = 0

top_left = (0, 0)
top_right = (0, 0)
bottom_left = (0, 0)
bottom_right = (0, 0)


def map_for_craziflie(tracked_pixel: tuple) -> tuple:
    # map (0, 0) to bottom, middle
    # map (-0.5, 0) to bottom, left
    # map (0.5, 0) to bottom, right
    # map (0, 0.5) to top, middle

    # get the x and y coordinates of the tracked pixel
    x, y = tracked_pixel

    if callibration_step != 5:
        return None
    
    width = top_right[0] - top_left[0]
    height = bottom_left[1] - top_left[1]


    distance_from_left = x - top_left[0]
    distance_from_top = y - top_left[1]

    scaled_x = distance_from_left / width # between 0 and 1
    scaled_y = distance_from_top / height # between 0 and 1

    shifted_x = scaled_x - 0.5
    flipped_y = 1 - scaled_y

    clamped_x = max(-0.5, min(0.5, shifted_x))
    clamped_y = max(0, min(1, flipped_y))

    return (clamped_x, clamped_y)

# ----------------------------- END KINECT FUNCTIONS ----------------------------------

# ------------------------------- MAIN LOOP ------------------------------------------

time_of_last_send = None
FREQUENCY = 15 # Hz

while True:
    frames = listener.waitForNewFrame()

    color = frames["color"]
    ir = frames["ir"]
    depth = frames["depth"]

    registration.apply(color, depth, undistorted, registered,
                       bigdepth=bigdepth,
                       color_depth_map=color_depth_map)

    # NOTE for visualization:
    # cv2.imshow without OpenGL backend seems to be quite slow to draw all
    # things below. Try commenting out some imshow if you don't have a fast
    # visualization backend.
    # cv2.imshow("ir", ir.asarray() / 65535.)
    tracked_pixel = find_average_center(limit_depth(depth.asarray(), 500, 900))
    mapped_pixel = map_for_craziflie(tracked_pixel)

    # draw a circle at the center of the tracked pixel onto the depth image
    depth_image = depth.asarray() / 4500.
    depth_image = cv2.cvtColor(depth_image, cv2.COLOR_GRAY2BGR)

    # get top left corner
    if callibration_step == 1:
        cv2.putText(depth_image, "Top Left", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 3, cv2.LINE_AA)
        cv2.putText(depth_image, str(int(3 - (time.time() - last_step_start))), (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 3, cv2.LINE_AA)


        if time.time() - last_step_start > 3:
            top_left = tracked_pixel
            last_step_start = time.time()
            callibration_step = 2

    # get top right corner
    elif callibration_step == 2:
        # draw the top left corner
        cv2.circle(depth_image, (int(top_left[0]), int(top_left[1])), 5, (255, 0, 0), -1)

        cv2.putText(depth_image, "Top Right", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 3, cv2.LINE_AA)
        cv2.putText(depth_image, str(int(3 - (time.time() - last_step_start))), (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 3, cv2.LINE_AA)

        if time.time() - last_step_start > 3:
            top_right = tracked_pixel
            last_step_start = time.time()
            callibration_step = 3

            # make sure the top left and top right corners are on the same y level
            lower_y = max(top_left[1], top_right[1])
            top_left = (top_left[0], lower_y)
            top_right = (top_right[0], lower_y)

            

    # get bottom left corner
    elif callibration_step == 3:
        # draw the top line
        cv2.line(depth_image, (int(top_left[0]), int(top_left[1])), (int(top_right[0]), int(top_left[1])), (255, 0, 0), 2)

        cv2.putText(depth_image, "Bottom Left", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 3, cv2.LINE_AA)
        cv2.putText(depth_image, str(int(3 - (time.time() - last_step_start))), (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 3, cv2.LINE_AA)

        if time.time() - last_step_start > 3:
            bottom_left = tracked_pixel
            last_step_start = time.time()
            callibration_step = 4

            # make sure the top left and bottom left corners are on the same x level
            right_x = max(top_left[0], bottom_left[0])
            top_left = (right_x, top_left[1])
            bottom_left = (right_x, bottom_left[1])

    # get bottom right corner
    elif callibration_step == 4:
        # draw the top line
        cv2.line(depth_image, (int(top_left[0]), int(top_left[1])), (int(top_right[0]), int(top_right[1])), (255, 0, 0), 2)

        # draw the left line
        cv2.line(depth_image, (int(top_left[0]), int(top_left[1])), (int(bottom_left[0]), int(bottom_left[1])), (255, 0, 0), 2)

        cv2.putText(depth_image, "Bottom Right", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 3, cv2.LINE_AA)
        cv2.putText(depth_image, str(int(3 - (time.time() - last_step_start))), (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 3, cv2.LINE_AA)

        if time.time() - last_step_start > 3:
            bottom_right = tracked_pixel
            last_step_start = time.time()
            callibration_step = 5

            # make sure the bottom left and bottom right corners are on the same y level
            higher_y = min(bottom_left[1], bottom_right[1])

            # make sure the top right and bottom right corners are on the same x level
            right_x = min(top_right[0], bottom_right[0])
            
            top_right = (right_x, top_right[1])
            bottom_right = (right_x, higher_y)
            bottom_left = (bottom_left[0], higher_y)

            if USING_ROS:
                requests.get(
                    f"http://{ROS_IP}:{ROS_PORT}/kinect/start"
                )

    elif callibration_step == 5:
        # draw square
        cv2.line(depth_image, (int(top_left[0]), int(top_left[1])), (int(top_right[0]), int(top_right[1])), (255, 0, 0), 2)
        cv2.line(depth_image, (int(top_left[0]), int(top_left[1])), (int(bottom_left[0]), int(bottom_left[1])), (255, 0, 0), 2)
        cv2.line(depth_image, (int(bottom_left[0]), int(bottom_left[1])), (int(bottom_right[0]), int(bottom_right[1])), (255, 0, 0), 2)
        cv2.line(depth_image, (int(bottom_right[0]), int(bottom_right[1])), (int(top_right[0]), int(top_right[1])), (255, 0, 0), 2)

        cv2.putText(depth_image, str((round(mapped_pixel[0], 3), round(mapped_pixel[1], 3))), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 3, cv2.LINE_AA)

        # we can start sending the mapped pixel to the craziflie and max
        # send_to_max(mapped_pixel[0], mapped_pixel[1])
        if time_of_last_send is None or (time.time() - time_of_last_send) > 1.0 / FREQUENCY:
            if USING_ROS:
                send_to_ros(mapped_pixel[0], mapped_pixel[1])
            if USING_MAX:
                send_to_max(mapped_pixel[0], mapped_pixel[1])
            time_of_last_send = time.time()

    # draw the tracked pixel
    cv2.circle(depth_image, (int(tracked_pixel[0]), int(tracked_pixel[1])), 5, (0, 0, 255), -1)
    cv2.imshow("depth", depth_image)

    listener.release(frames)

    key = cv2.waitKey(delay=1)
    if key == ord(' '):
        callibration_step += 1
        last_step_start = time.time()

    if key == ord('q'):
        break

# exit the ROS device
_ = requests.get(
    f"http://{ROS_IP}:{ROS_PORT}/kinect/exit"
)

device.stop()
device.close()

sys.exit(0)
