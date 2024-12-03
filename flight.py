
import threading 
import time
import queue

from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.dispatcher import Dispatcher

import numpy as np
from blocklyTranslations import *
from crazyflie_py import Crazyswarm

sensor_queue = queue.Queue(maxsize=0)

def read_sensor(address, *args):
    sensor_num = address[-1]
    sensor_queue.put((sensor_num, args[0]))

dispatcher = Dispatcher()
dispatcher.map("/sensor/*", read_sensor) 

def sensor_loop():
    server = ThreadingOSCUDPServer(("127.0.0.1", 7001), dispatcher)
    server.serve_forever()
    
def flight_loop():
    while True:
        try:
            value = sensor_queue.get_nowait()
            print(value)
        except queue.Empty:
            print("No value; ignoring...")
            pass

        time.sleep(0.5)

def test_flight_loop():
    Z = 1

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
            Z = 1 + (0.3125 * i)
            
            duration = 1
            for cf in allcfs.crazyflies:
                pos = np.array(cf.initialPosition) + np.array([0, 0, Z])
                cf.goTo(pos, 0, duration)
            
            # does this pause the loop or just the drone ?
            timeHelper.sleep(duration)
    
    for cf in crazyflies:
        cf.land(0.04, 2.0)
    
    timeHelper.sleep(2.0)
    pass

# Create threads for each loop
t1 = threading.Thread(target=sensor_loop)
t2 = threading.Thread(target=test_flight_loop)

t1.start()
t2.start()
