from controller import Robot
import struct
from typing import Tuple
import socket
import json
import time
import math

UDP_IP = "127.0.0.1"
UDP_PORT = 12345
client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_sock.settimeout(0.1)

TIME_STEP = 64
ROBOT_NAMES = ["B1", "B2", "B3", "Y1", "Y2", "Y3"]
N_ROBOTS = len(ROBOT_NAMES)

robot = Robot()
robot_name = robot.getName()
robot_color = robot_name[0] # B/Y

receiver = robot.getDevice("supervisor receiver")
receiver.enable(TIME_STEP)

team_emitter = robot.getDevice("team emitter")
team_receiver = robot.getDevice("team receiver")
team_receiver.enable(TIME_STEP)

ball_receiver = robot.getDevice("ball receiver")
ball_receiver.enable(TIME_STEP)

gps = robot.getDevice("gps")
gps.enable(TIME_STEP)

compass = robot.getDevice("compass")
compass.enable(TIME_STEP)

sonar_left = robot.getDevice("distancesensor left")
sonar_left.enable(TIME_STEP)
sonar_right = robot.getDevice("distancesensor right")
sonar_right.enable(TIME_STEP)
sonar_front = robot.getDevice("distancesensor front")
sonar_front.enable(TIME_STEP)
sonar_back = robot.getDevice("distancesensor back")
sonar_back.enable(TIME_STEP)

left_motor = robot.getDevice("left wheel motor")
right_motor = robot.getDevice("right wheel motor")

left_motor.setPosition(float('+inf'))
right_motor.setPosition(float('+inf'))

left_motor.setVelocity(0.0)
right_motor.setVelocity(0.0)

def receive_latest_data(receiver):
    packet = None
    direction = None
    strength = None
    counter = 0
    while receiver.getQueueLength() > 0:
        counter = counter + 1
        packet = receiver.getData()
        direction = receiver.getEmitterDirection()
        strength = receiver.getSignalStrength()
        receiver.nextPacket()
    if counter > 1:
        print(robot.getName(), "-", receiver.getName(), "- Packets lost:", counter - 1)
    return (packet, direction, strength)

def add_supervisor_data(data):
    packet, _, _ = receive_latest_data(receiver)
    if packet is None: return
    struct_fmt = "?"
    unpacked = struct.unpack(struct_fmt, packet)
    data["waiting_for_kickoff"] = unpacked[0]

def add_team_data(data):
    packet, _, _ = receive_latest_data(team_receiver)
    if packet is None: return
    struct_fmt = "i"
    unpacked = struct.unpack(struct_fmt, packet)
    data["robot_id"] = unpacked[0]

def add_ball_data(data):
    _, direction, strength = receive_latest_data(ball_receiver)
    ball_data = {}
    ball_data["direction"] = direction
    ball_data["strength"] = strength
    data["ball"] = ball_data

def send_data_to_team(robot_id) -> None:
    """Send data to the team

    Args:
            robot_id (int): ID of the robot
    """
    struct_fmt = "i"
    data = [robot_id]
    packet = struct.pack(struct_fmt, *data)
    team_emitter.send(packet)


def get_gps_coordinates() -> list:
    """Get new GPS coordinates

    Returns:
        List containing x and y values
    """
    gps_values = gps.getValues()
    return [gps_values[0], gps_values[1]]

def get_compass_heading() -> float:
    """Get compass heading in radians

    Returns:
        float: Compass value in radians
    """
    compass_values = compass.getValues()

    # Add math.pi/2 (90) so that the heading 0 is facing opponent's goal
    rad = math.atan2(compass_values[0], compass_values[1]) + (math.pi / 2)
    if rad < -math.pi:
        rad = rad + (2 * math.pi)

    return rad

def get_sonar_values() -> dict:
    """Get new values from sonars.

    Returns:
        dict: Value for each sonar.
    """
    return {
        "left": sonar_left.getValue(),
        "right": sonar_right.getValue(),
        "front": sonar_front.getValue(),
        "back": sonar_back.getValue(),
    }

def add_robot_data(data):
    robot_data = {}
    robot_data["name"] = robot_name
    robot_data["position"] = get_gps_coordinates()
    robot_data["rotation"] = get_compass_heading()
    robot_data["sonar"] = get_sonar_values()
    data["robot"] = robot_data

def collect_data():
    data = {}
    add_supervisor_data(data)
    add_team_data(data)
    add_ball_data(data)
    add_robot_data(data)

    data["color"] = robot_color
    data["time"] = robot.getTime()
    return data


while robot.step(TIME_STEP) != -1:
    try:
        begin_time = time.time()
        data = collect_data()

        data = json.dumps(data)
        data = data.encode("utf8")
        client_sock.sendto(data, (UDP_IP, UDP_PORT))

        data, addr = client_sock.recvfrom(1024)
        #print(f"received message: {data} from {addr}")
        data = json.loads(data)
        left_motor.setVelocity(data[robot.getName()]["L"])
        right_motor.setVelocity(data[robot.getName()]["R"])
        end_time = time.time()
        diff_time = round((end_time - begin_time)*1000)
        if diff_time > TIME_STEP:
            print(robot.getName(), "- Delay:" , str(diff_time) , "ms")
    except Exception as e:
        print(e)


client_sock.close()
