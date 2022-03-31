
import math
def get_direction(ball_vector: list) -> int:
    """Get direction to navigate robot to face the ball

    Args:
        ball_vector (list of floats): Current vector of the ball with respect
            to the robot.

    Returns:
        int: 0 = forward, -1 = right, 1 = left
    """
    if -0.13 <= ball_vector[1] <= 0.13:
        return 0
    return -1 if ball_vector[1] < 0 else 1

class World:
    def __init__(self):
        self.wfk=False
        self.robots=[{"x":0, "y":0, "rot":0}, {"x":0, "y":0, "rot":0}, {"x":0, "y":0, "rot":0}]
        self.ball={"x":0, "y":0}

    def setRobot(self, id, x, y, rot):
        self.robots[id]={"x":x, "y":y, "rot":rot}
    
    def getRobot(self, id):
        return self.robots[id]
    
    def setBall(self, x, y):
        self.ball={"x":x, "y":y}
        
    def getBall(self):
        return self.ball


def angleBetweenPoints(x1, y1, x2, y2):
    return math.atan2(y2 - y1, x2 - x1)
    