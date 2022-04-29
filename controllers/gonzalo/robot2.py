# rcj_soccer_player controller - ROBOT B2

# Feel free to import built-in libraries
import math  # noqa: F401

# You can also import scripts that you put into the folder with controller
import utils
from rcj_soccer_robot import RCJSoccerRobot, TIME_STEP


class MyRobot2(RCJSoccerRobot):
    def run(self):
        while self.robot.step(TIME_STEP) != -1:

            # El mundo sabe si está esperando kick, posición de cada robot del equipo y posición de la pelota
            self.refreshWorld()
            sonar_values = self.get_sonar_values()
            # if self.world.getBall()["x"] != -100:
            # self.goToBall()
            # self.goToPoint(0,0)
            if self.world.getBall()["x"] != -100:
                # self.lookAtAPoint(self.world.getBall()["x"], self.world.getBall()["y"])
                self.goToPoint(
                    self.world.getBall()["x"], self.world.getBall()["y"], 2
                )
            else:
                self.setVelocity(-self.MAX_VEL / 4, self.MAX_VEL / 4)
            # self.setVelocity(100, 100)
            # Send message to team robots
            self.send_data_to_team()
            # self.stop()
            self.setVelocity(-1, 1)
