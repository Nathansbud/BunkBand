
import threading 
import time

from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.dispatcher import Dispatcher

# from crazyflie_py import Crazyswarm
# from blocklyTranslations import *

def read_sensor(address, *args):
    print(address, args)

dispatcher = Dispatcher()
dispatcher.map("/sensor/*", read_sensor) 

def sensor_loop():
    server = ThreadingOSCUDPServer(("127.0.0.1", 6813), dispatcher)
    server.serve_forever()
    
def flight_loop():
    # TODO: Crazyflie flight stuff!

    # swarm = Crazyswarm()
    # crazyflies = swarm.allcfs.crazyflies
    # timeHelper = swarm.timeHelper

    # groupState = SimpleNamespace(crazyflies=crazyflies, timeHelper=timeHelper)

    # Takeoff method from blocklyTranslations
    # takeoff(groupState, height=1.25, duration=3)
    pass

# Create threads for each loop
t1 = threading.Thread(target=sensor_loop)
t2 = threading.Thread(target=flight_loop)

t1.start()
t2.start()
