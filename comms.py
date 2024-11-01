import time
import serial

from random import randint
from pythonosc.udp_client import SimpleUDPClient

SERVER_IP = "127.0.0.1"
SERVER_PORT = 6813

arduino = serial.Serial(port="/dev/tty.usbmodem4827E2E12D2C2", baudrate=115200)
client = SimpleUDPClient(SERVER_IP, SERVER_PORT)

while True:
    reading = arduino.readline().decode().strip()

    # truncated reading, ignore
    if "-" not in reading: 
        continue

    sensor, value = reading.split("-") 
    client.send_message(f"/sensor/{sensor}", int(value))
