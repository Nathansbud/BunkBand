import time
import serial

from random import randint
from pythonosc.udp_client import SimpleUDPClient

SERVER_IP = "127.0.0.1"

R4 = "/dev/tty.usbmodem4827E2E12D2C2"
R2 = "/dev/cu.usbmodem142202"

arduino = serial.Serial(port=R2, baudrate=9600)

max_client = SimpleUDPClient(SERVER_IP, 6813)
robot_client = SimpleUDPClient(SERVER_IP, 7001)

ACTIVE = 0

BUCKET = 0
COUNT = 0

while True:
    reading = arduino.readline().decode().strip()
    # truncated reading, ignore
    if "-" not in reading: 
        continue

    sensor_raw, value_raw = reading.split("-")
    sensor, value = int(sensor_raw), float(value_raw)

    # print(value)

    proposed = 0
    if 0 < value <= 10:
        proposed = 1
    elif 10 < value <= 25:
        proposed = 2
    elif 25 < value <= 40:
        proposed = 3
    elif 40 < value <= 60:
        proposed = 4
    elif 60 < value <= 100:
        proposed = 5
    else:
        proposed = 0
    
    if proposed == BUCKET:
        COUNT += 1
    else:
        BUCKET = proposed
        COUNT = 1
    
    if COUNT == 5 and ACTIVE != BUCKET:
        print(f"Changing active bucket to {proposed}...")
        ACTIVE = BUCKET
        
        max_client.send_message(f"/sensor/{sensor}", BUCKET - 1)
        robot_client.send_message(f"/sensor/{sensor}", BUCKET - 1)
