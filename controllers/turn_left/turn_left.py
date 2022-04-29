from controller import Robot

TIME_STEP = 64

robot = Robot()

left_motor = robot.getDevice("left wheel motor")
right_motor = robot.getDevice("right wheel motor")

left_motor.setPosition(float("+inf"))
right_motor.setPosition(float("+inf"))

while robot.step(TIME_STEP) != -1:
    left_motor.setVelocity(10.0)
    right_motor.setVelocity(-10.0)
