import time
import serial
import requests


from random import randint
from pythonosc.udp_client import SimpleUDPClient

ROS_IP = "138.16.161.225"
MAX_IP = "127.0.0.1"

MAX_PORT = 6813
ROS_PORT = 7001

NETWORKED = False

R4 = "/dev/tty.usbmodem4827E2E12D2C2"
R2 = "/dev/cu.usbmodem14102"

arduino = serial.Serial(port=R2, baudrate=9600)
max_client = SimpleUDPClient(MAX_IP, MAX_PORT)

reading_map = {
    i: {
        "active": 0,
        "bucket": 0,
        "count": 0
    } for i in range(4)
}

while True:
    reading = arduino.readline().decode().strip()
    # truncated reading, ignore
    if "-" not in reading: 
        continue

    sensor_raw, value_raw = reading.split("-")
    sensor, value = int(sensor_raw), float(value_raw)

    proposed = 0    
    # More conservative buckets
    if 0 <= value <= 5:
        proposed = 1
    elif 5 < value <= 15:
        proposed = 2
    elif 15 < value <= 25:
        proposed = 3
    elif 25 < value <= 35:
        proposed = 4
    elif 35 < value <= 45:
        proposed = 5
    else:
        proposed = 0
    
    if proposed == reading_map[sensor]["bucket"]:
        reading_map[sensor]["count"] += 1
    else:
        reading_map[sensor]["bucket"] = proposed
        reading_map[sensor]["count"] = 1
    
    if reading_map[sensor]["active"] != reading_map[sensor]["bucket"] and reading_map[sensor]["count"] == 5:
        print(f"Changing S{sensor} active bucket to {proposed}...")
        
        reading_map[sensor]["active"] = reading_map[sensor]["bucket"]
        
        # if we have an activity reading, change our locale
        if reading_map[sensor]["active"] != 0:
            print("should send...")

            # # Send the sensor update to Max
            max_client.send_message(f"/sensor/{sensor}", reading_map[sensor]["bucket"] - 1)
            # # Send message TO THE ROS device!
            
            if NETWORKED:
                _ = requests.get(
                    f"http://{ROS_IP}:{ROS_PORT}/sensor/{sensor}/{reading_map[sensor]['bucket']-1}"
                )
