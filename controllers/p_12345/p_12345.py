from controller import Robot
import struct
import socket
import json
import time
import math

UDP_IP = "127.0.0.1"
UDP_PORT = 12345
client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_sock.settimeout(0.1)

TIME_STEP = 32
ROBOT_NAMES = ["B1", "B2", "B3", "Y1", "Y2", "Y3"]
N_ROBOTS = len(ROBOT_NAMES)

robot = Robot()
robot_name = robot.getName()
robot_color = robot_name[0] # B/Y
robot_idx = int(robot_name[1]) - 1

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

def receive_all_data(receiver):
    data = []
    while receiver.getQueueLength() > 0:
        packet = receiver.getData()
        direction = receiver.getEmitterDirection()
        strength = receiver.getSignalStrength()
        data.append((packet, direction, strength))
        receiver.nextPacket()
    if len(data) == 0: return None
    return data

def add_supervisor_data(data):
    packet, _, _ = receive_latest_data(receiver)
    if packet is None: return
    struct_fmt = "?"
    unpacked = struct.unpack(struct_fmt, packet)
    data["waiting_for_kickoff"] = unpacked[0]

def add_team_data(data):
    in_data = receive_all_data(team_receiver)
    if in_data is None: return
    data["team"] = [json.loads(packet.decode("utf8")) for packet, _, _ in in_data]
    
def send_team_data(data):
    if data is None: return
    packet = json.dumps(data).encode("utf8")
    team_emitter.send(packet)

def add_ball_data(data):
    _, direction, strength = receive_latest_data(ball_receiver)
    if direction is None or strength is None: return
    ball_data = {}
    ball_data["direction"] = direction
    ball_data["strength"] = strength
    data["ball"] = ball_data

def get_gps_coordinates() -> list:
    return gps.getValues()

def get_compass_values() -> float:
    return compass.getValues()

def get_sonar_values() -> dict:
    return {
        "left": sonar_left.getValue(),
        "right": sonar_right.getValue(),
        "front": sonar_front.getValue(),
        "back": sonar_back.getValue(),
    }

def add_robot_data(data):
    robot_data = {}
    robot_data["name"] = robot_name
    robot_data["color"] = robot_color
    robot_data["index"] = robot_idx
    robot_data["gps"] = get_gps_coordinates()
    robot_data["compass"] = get_compass_values()
    robot_data["sonar"] = get_sonar_values()
    data["robot"] = robot_data

def collect_data():
    data = {}
    data["time"] = robot.getTime()
    add_supervisor_data(data)
    add_ball_data(data)
    add_robot_data(data)
    add_team_data(data)
    return data

while robot.step(TIME_STEP) != -1:
    try:
        begin_time = time.time()

        data = collect_data()
        data = json.dumps(data).encode("utf8")
        client_sock.sendto(data, (UDP_IP, UDP_PORT))

        data, addr = client_sock.recvfrom(1024)
        #print(f"received message: {data} from {addr}")
        data = json.loads(data)

        for msg in data.get("team") or []:
            send_team_data(msg)

        left_motor.setVelocity(data["L"])
        right_motor.setVelocity(data["R"])

        end_time = time.time()
        diff_time = round((end_time - begin_time)*1000)
        if diff_time > TIME_STEP:
            print(robot_name, "- Delay:" , str(diff_time) , "ms")
    except Exception as e:
        print(robot_name, "-", e)

client_sock.close()
