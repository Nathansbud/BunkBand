# coding: utf-8

import time
import numpy as np
import cv2
import sys
from pylibfreenect2 import Freenect2, SyncMultiFrameListener
from pylibfreenect2 import FrameType, Registration, Frame
from pylibfreenect2 import createConsoleLogger, setGlobalLogger
from pylibfreenect2 import LoggerLevel

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

    return (shifted_x, flipped_y)

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

    # draw a circle at the center of the tracked pixel onto the depth image
    depth_image = depth.asarray() / 4500.
    depth_image = cv2.cvtColor(depth_image, cv2.COLOR_GRAY2BGR)

    # get top left corner
    if callibration_step == 1:
        if time.time() - last_step_start > 5:
            top_left = tracked_pixel
            last_step_start = time.time()
            callibration_step = 2

    # get top right corner
    elif callibration_step == 2:
        # draw the top left corner
        cv2.circle(depth_image, (int(top_left[0]), int(top_left[1])), 5, (255, 0, 0), -1)

        if time.time() - last_step_start > 5:
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

        if time.time() - last_step_start > 5:
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

        if time.time() - last_step_start > 5:
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
    else:
        # draw square
        cv2.line(depth_image, (int(top_left[0]), int(top_left[1])), (int(top_right[0]), int(top_right[1])), (255, 0, 0), 2)
        cv2.line(depth_image, (int(top_left[0]), int(top_left[1])), (int(bottom_left[0]), int(bottom_left[1])), (255, 0, 0), 2)
        cv2.line(depth_image, (int(bottom_left[0]), int(bottom_left[1])), (int(bottom_right[0]), int(bottom_right[1])), (255, 0, 0), 2)
        cv2.line(depth_image, (int(bottom_right[0]), int(bottom_right[1])), (int(top_right[0]), int(top_right[1])), (255, 0, 0), 2)
    

    # draw the tracked pixel
    cv2.circle(depth_image, (int(tracked_pixel[0]), int(tracked_pixel[1])), 5, (0, 0, 255), -1)

    print(tracked_pixel)
    print(map_for_craziflie(tracked_pixel))

    cv2.imshow("depth", depth_image)
    

    
    # cv2.imshow("color", cv2.resize(color.asarray(),
                                #    (int(1920 / 3), int(1080 / 3))))
    # cv2.imshow("registered", registered.asarray(np.uint8))

    # if need_bigdepth:
    #     cv2.imshow("bigdepth", cv2.resize(bigdepth.asarray(np.float32),
    #                                       (int(1920 / 3), int(1082 / 3))))
    # if need_color_depth_map:
    #     cv2.imshow("color_depth_map", color_depth_map.reshape(424, 512))

    listener.release(frames)

    key = cv2.waitKey(delay=1)
    if key == ord(' '):
        callibration_step += 1
        last_step_start = time.time()

    if key == ord('q'):
        break

device.stop()
device.close()

sys.exit(0)
