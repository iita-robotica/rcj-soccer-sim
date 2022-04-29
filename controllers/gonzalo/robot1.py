# rcj_soccer_player controller - ROBOT B1

# Feel free to import built-in libraries
import math  # noqa: F401

# You can also import scripts that you put into the folder with controller
import utils
from rcj_soccer_robot import RCJSoccerRobot, TIME_STEP


class MyRobot1(RCJSoccerRobot):
    def run(self):
        while self.robot.step(TIME_STEP) != -1:

            # El mundo sabe si está esperando kick, posición de cada robot del equipo y posición de la pelota
            self.refreshWorld()
            sonar_values = self.get_sonar_values()
            self.goToBall()

            # Send message to team robots
            self.send_data_to_team()
            self.stop()
