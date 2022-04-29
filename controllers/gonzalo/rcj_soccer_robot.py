import math
import struct

from angles import d2r, normalize, r2d
from utils import angleBetweenPoints, World

TIME_STEP = 64
ROBOT_NAMES = ["B1", "B2", "B3", "Y1", "Y2", "Y3"]
N_ROBOTS = len(ROBOT_NAMES)
ball_ant = [0, 0]


class RCJSoccerRobot:
    def __init__(self, robot):
        self.robot = robot
        self.name = self.robot.getName()
        self.team = self.name[0]
        self.player_id = int(self.name[1])

        self.receiver = self.robot.getDevice("supervisor receiver")
        self.receiver.enable(TIME_STEP)

        self.team_emitter = self.robot.getDevice("team emitter")
        self.team_receiver = self.robot.getDevice("team receiver")
        self.team_receiver.enable(TIME_STEP)

        self.ball_receiver = self.robot.getDevice("ball receiver")
        self.ball_receiver.enable(TIME_STEP)

        self.gps = self.robot.getDevice("gps")
        self.gps.enable(TIME_STEP)

        self.compass = self.robot.getDevice("compass")
        self.compass.enable(TIME_STEP)

        self.sonar_left = self.robot.getDevice("distancesensor left")
        self.sonar_left.enable(TIME_STEP)
        self.sonar_right = self.robot.getDevice("distancesensor right")
        self.sonar_right.enable(TIME_STEP)
        self.sonar_front = self.robot.getDevice("distancesensor front")
        self.sonar_front.enable(TIME_STEP)
        self.sonar_back = self.robot.getDevice("distancesensor back")
        self.sonar_back.enable(TIME_STEP)

        self.left_motor = self.robot.getDevice("left wheel motor")
        self.right_motor = self.robot.getDevice("right wheel motor")

        self.left_motor.setPosition(float("+inf"))
        self.right_motor.setPosition(float("+inf"))

        self.left_motor.setVelocity(0.0)
        self.right_motor.setVelocity(0.0)

        self.world = World()
        self.MAX_VEL = 10

    def parse_supervisor_msg(self, packet: str) -> dict:
        """Parse message received from supervisor

        Returns:
            dict: Location info about each robot and the ball.
            Example:
                {
                    'waiting_for_kickoff': False,
                }
        """
        # True/False telling whether the goal was scored
        struct_fmt = "?"
        unpacked = struct.unpack(struct_fmt, packet)

        data = {"waiting_for_kickoff": unpacked[0]}
        return data

    def get_new_data(self) -> dict:
        """Read new data from supervisor

        Returns:
            dict: See `parse_supervisor_msg` method
        """
        packet = self.receiver.getData()
        self.receiver.nextPacket()

        return self.parse_supervisor_msg(packet)

    def is_new_data(self) -> bool:
        """Check if there is new data from supervisor to be received

        Returns:
            bool: Whether there is new data received from supervisor.
        """
        return self.receiver.getQueueLength() > 0

    def parse_team_msg(self, packet: str) -> dict:
        """Parse message received from team robot

        Returns:
            dict: Parsed message stored in dictionary.
        """
        struct_fmt = "i"
        unpacked = struct.unpack(struct_fmt, packet)
        data = {
            "robot_id": unpacked[0],
            "x": unpacked[1],
            "y": unpacked[2],
            "rotation": unpacked[3],
            "ballX": unpacked[4],
            "ballY": unpacked[5],
        }
        return data

    def get_new_team_data(self) -> dict:
        """Read new data from team robot

        Returns:
            dict: See `parse_team_msg` method
        """
        packet = self.team_receiver.getData()
        self.team_receiver.nextPacket()
        return self.parse_team_msg(packet)

    def is_new_team_data(self) -> bool:
        """Check if there is new data from team robots to be received

        Returns:
            bool: Whether there is new data received from team robots.
        """
        return self.team_receiver.getQueueLength() > 0

    def send_data_to_team(self) -> None:
        """Send data to the team

        Args:
             robot_id (int): ID of the robot
        """
        struct_fmt = "i f f f f f"

        data = [
            self.player_id,
            self.get_gps_coordinates()[0],
            self.get_gps_coordinates()[1],
            self.get_compass_heading(),
            self.world.getBall()["x"],
            self.world.getBall()["y"],
        ]
        packet = struct.pack(struct_fmt, *data)
        self.team_emitter.send(packet)

    def get_new_ball_data(self) -> dict:
        """Read new data from IR sensor

        Returns:
            dict: Direction and strength of the ball signal
            Direction is normalized vector indicating the direction of the
            emitter with respect to the receiver's coordinate system.
            Example:
                {
                    'direction': [0.23, -0.10, 0.96],
                    'strength': 0.1
                }
        """
        _ = self.ball_receiver.getData()
        data = {
            "direction": self.ball_receiver.getEmitterDirection(),
            "strength": self.ball_receiver.getSignalStrength(),
        }

        distancia = math.sqrt(1 / data["strength"])
        x = data["direction"][0]
        y = data["direction"][1]
        rx = self.get_gps_coordinates()[0]
        ry = self.get_gps_coordinates()[1]
        # print(rx,ry,x,y, distancia)
        da = math.atan2(y, x)
        da = normalize(da, -math.pi, math.pi)
        # print(da, self.get_compass_heading())
        a = self.get_compass_heading() + da
        a = normalize(a, -math.pi, math.pi)
        # print(r2d(self.get_compass_heading()), r2d(da), r2d(a))

        dx = math.sin(a) * distancia + rx
        dy = -math.cos(a) * distancia + ry

        data = {"x": dx, "y": dy}
        # print(data, rx, ry)
        self.ball_receiver.nextPacket()
        return data

    def is_new_ball_data(self) -> bool:
        """Check if there is new data from ball to be received

        Returns:
            bool: Whether there is new data received from ball.
        """
        return self.ball_receiver.getQueueLength() > 0

    def get_gps_coordinates(self) -> list:
        """Get new GPS coordinates

        Returns:
            List containing x and y values
        """
        gps_values = self.gps.getValues()
        return [gps_values[0], gps_values[1]]

    def get_compass_heading(self) -> float:
        """Get compass heading in radians

        Returns:
            float: Compass value in radians
        """
        compass_values = self.compass.getValues()

        # Add math.pi/2 (90) so that the heading 0 is facing opponent's goal
        rad = math.atan2(compass_values[0], compass_values[1]) + (math.pi / 2)

        rad = normalize(rad, -math.pi, math.pi)

        return rad

    def get_sonar_values(self) -> dict:
        """Get new values from sonars.

        Returns:
            dict: Value for each sonar.
        """
        return {
            "left": self.sonar_left.getValue(),
            "right": self.sonar_right.getValue(),
            "front": self.sonar_front.getValue(),
            "back": self.sonar_back.getValue(),
        }

    def goToBall(self):
        """Go to ball"""
        # ACAACA Rehacer
        # Compute the speed for motors
        direction = self.world.ball["direction"]

        # If the robot has the ball right in front of it, go forward,
        # rotate otherwise
        if direction == 0:
            left_speed = 5
            right_speed = 5
        else:
            left_speed = direction * 4
            right_speed = direction * -4

        # Set the speed to motors
        self.left_motor.setVelocity(left_speed)
        self.right_motor.setVelocity(right_speed)
        return True

    def lookAtAPoint(self, x, y, thresh=5):
        deg = r2d(
            angleBetweenPoints(
                x,
                y,
                self.get_gps_coordinates()[0],
                self.get_gps_coordinates()[1],
            )
            + math.pi / 2
        )
        deg = normalize(deg, -180, 180)
        rot = r2d(self.get_compass_heading())
        final = deg - rot
        # print("Calculo ori:", final)
        if final > 90:
            final = final - 180
        if final < -90:
            final = final + 180

        dir = 1
        vel = abs(final / 9)
        if abs(final) <= thresh:
            vl = 0
            vr = 0
        else:
            if final > 0:
                vl = -vel * dir
                vr = vel * dir
            else:
                vl = vel * dir
                vr = -vel * dir

        self.setVelocity(vl, vr)

    def goToPoint(self, x, y, thresh):
        """Go to point x y"""
        deg = r2d(
            angleBetweenPoints(
                x,
                y,
                self.get_gps_coordinates()[0],
                self.get_gps_coordinates()[1],
            )
            + math.pi / 2
        )
        deg = normalize(deg, -180, 180)
        rot = r2d(self.get_compass_heading())
        final = deg - rot

        dist = math.sqrt(
            (x - self.get_gps_coordinates()[0]) ** 2
            + (y - self.get_gps_coordinates()[1]) ** 2
        )

        if final > 90:
            final = final - 180
        if final < -90:
            final = final + 180

        dir = 1
        dif = abs(final / 9) * 0.5 + (1 / dist) * 0.5
        if abs(final * dist) <= thresh:
            vl = self.MAX_VEL
            vr = self.MAX_VEL
        else:
            if final > 0:
                vr = self.MAX_VEL
                vl = self.MAX_VEL - dif

            else:
                vl = self.MAX_VEL
                vr = self.MAX_VEL - dif

        self.setVelocity(vl, vr)

    def stop(self):
        self.left_motor.setVelocity(0)
        self.right_motor.setVelocity(0)

    def setVelocity(self, vl, vr):
        self.left_motor.setVelocity(vr)
        self.right_motor.setVelocity(vl)

    def refreshWorld(self):
        if self.is_new_data():
            self.world.wfk = self.get_new_data()  # noqa: F841

        while self.is_new_team_data():
            team_data = self.get_new_team_data()
            self.world.setRobot(
                team_data["robot_id"],
                team_data["x"],
                team_data["y"],
                team_data["rotation"],
            )
            # print(team_data)
            if team_data["ballX"] != -100:
                print(team_data["ball_x"], team_data["ball_y"])
                self.world.setBall(team_data["ball_x"], team_data["ball_y"])

        self.world.setRobot(
            self.player_id,
            self.get_gps_coordinates()[0],
            self.get_gps_coordinates()[1],
            self.get_compass_heading(),
        )

        if self.is_new_ball_data():
            ball_data = self.get_new_ball_data()
            self.world.setBall(ball_data["x"], ball_data["y"])
        else:
            self.world.setBall(-100, -100)

    def run(self):
        raise NotImplementedError
