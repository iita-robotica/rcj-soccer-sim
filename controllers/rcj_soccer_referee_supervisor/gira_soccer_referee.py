import json
import math
import os
import random
import time

watchdog_installed = False
try:
    from watchdog.events import PatternMatchingEventHandler
    from watchdog.observers import Observer

    watchdog_installed = True
except Exception:
    print(
        "Watchdog module not installed, automatic controller"
        " reload disabled. To enable, run 'pip install watchdog'"
    )

from referee.consts import (
    BALL_DEPTH,
    FIELD_X_LOWER_LIMIT,
    FIELD_X_UPPER_LIMIT,
    FIELD_Y_LOWER_LIMIT,
    FIELD_Y_UPPER_LIMIT,
    TIME_STEP,
)
from referee.referee import RCJSoccerReferee
from referee.utils import time_to_string

STATE_FILE = "state.json"
CONTROLLERS_DIR = ".."
SUPERVISOR_NAME = os.path.split(os.getcwd())[1]


def print_msg(key, args, response_id):
    kargs = ", ".join([f"{k}: {args[k]}" for k in args])
    msg = f">>> supervisor.{key}({kargs})"
    if response_id is not None:
        msg = msg + f" -> {response_id}"
    print(msg)


class GIRASoccerReferee(RCJSoccerReferee):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.pending_messages = []

        self.reset_controllers_flag = False
        self.reset_controllers_last_time = time.time()

        self.restoreState()
        self.start_watchdog()

    def saveState(self):
        try:
            timer_flag = self.check_timer_flag
            progress_flag = self.check_progress_flag
            goal_flag = self.check_goal_flag
            robots_in_area_flag = self.check_robots_in_penalty_area_flag
            data = {
                "Y": self.get_current_controller("Y"),
                "B": self.get_current_controller("B"),
                "saved_snapshot": self.saved_snapshot,
                "check_timer_flag": timer_flag,
                "check_progress_flag": progress_flag,
                "check_goal_flag": goal_flag,
                "check_robots_in_penalty_area_flag": robots_in_area_flag,
            }
            with open(STATE_FILE, "w") as file:
                json.dump(data, file)
        except Exception:
            print(f"El archivo {STATE_FILE} no se pudo escribir")

    def restoreState(self):
        try:
            with open(STATE_FILE) as file:
                data = json.load(file)

            self.saved_snapshot = data.get("saved_snapshot", None)
            self.check_timer_flag = data.get("check_timer_flag", True)
            self.check_progress_flag = data.get("check_progress_flag", True)
            self.check_robots_in_penalty_area_flag = data.get(
                "check_robots_in_penalty_area_flag", True
            )
            self.check_goal_flag = data.get("check_goal_flag", True)
            if "Y" in data:
                self.set_controller("Y", data["Y"])
            if "B" in data:
                self.set_controller("B", data["B"])
        except Exception:
            print(f"El archivo {STATE_FILE} no se pudo leer")
            self.saved_snapshot = None
            self.check_timer_flag = True
            self.check_progress_flag = True
            self.check_robots_in_penalty_area_flag = True
            self.check_goal_flag = True

    def start_watchdog(self):
        if not watchdog_installed:
            return

        def on_any_event(_):
            self.reset_controllers_flag = True

        event_handler = PatternMatchingEventHandler(
            patterns=["*.py"], ignore_patterns=[], ignore_directories=True
        )
        event_handler.on_any_event = on_any_event
        path = CONTROLLERS_DIR

        self.observer = Observer()
        self.observer.schedule(event_handler, path, recursive=True)
        self.observer.start()

    def stop_watchdog(self):
        if not watchdog_installed:
            return
        self.observer.stop()

    def send(self, __key, **args):
        messageString = json.dumps({"msg": __key, "args": args})
        self.sv.wwiSendText(messageString)

    def alert(self, msg):
        self.send("alert", message=msg)

    def log(self, msg):
        self.send("log", message=msg)

    def check_progress(self):
        if self.check_progress_flag:
            super().check_progress()

    def check_goal(self):
        if self.check_goal_flag:
            super().check_goal()

    def check_robots_in_penalty_area(self):
        if self.check_robots_in_penalty_area_flag:
            super().check_robots_in_penalty_area()

    def get_current_controller(self, team_name):
        return next(
            map(
                lambda n: self.sv.robot_nodes[n]
                .getField("controller")
                .getSFString(),
                filter(lambda n: n[0] == team_name, self.sv.robot_nodes),
            )
        )

    def tick(self):
        self.checkWatchdog()
        self.checkIncomingMessages()
        self.sendCurrentState()

        return_value = super().tick()

        if self.check_timer_flag:
            if not return_value:
                self.send("game_over")
                self.sv.step(TIME_STEP)
            return return_value
        else:
            if self.time < TIME_STEP / 1000.0:
                self.time = TIME_STEP / 1000.0
            return True

    def sendCurrentState(self):
        selected = self.sv.getSelected()
        self.send(
            "update",
            time=self.sv.getTime(),
            selected=selected.getDef() if selected is not None else None,
            ball_translation=self.sv.ball_translation,
            robot_translation=self.sv.robot_translation,
            robot_rotation=self.sv.robot_rotation,
            goal=self.ball_reset_timer > 0,
            messages=self.pending_messages,
        )
        self.pending_messages = []

    def add_event_message_to_queue(self, message: str):
        if self.time >= 0:
            msg_string = f"{time_to_string(self.time)} - {message}"
        else:
            msg_string = f"0:00 - {message}"
        self.pending_messages.append(msg_string)
        return super().add_event_message_to_queue(message)

    def checkWatchdog(self):
        if self.reset_controllers_flag:
            if time.time() - self.reset_controllers_last_time > 1:
                self.update_controllers_list()
                self.reset_controllers()
                self.reset_controllers_flag = False
                self.reset_controllers_last_time = time.time()

    def checkIncomingMessages(self):  # noqa: C901
        # Get the message in from the robot window(if there is one)
        message_text = self.sv.wwiReceiveText()

        # If there is a message
        if message_text != "":
            try:
                message = json.loads(message_text)
                key = message["msg"]
                args = message["args"]
                response_id = message["response_id"]

                print_msg(key, args, response_id)

                if key == "setup":
                    self.update_controllers_list()
                    self.update_flags()
                elif key == "reset":
                    self.reset_controllers()
                elif key == "set_controller":
                    self.set_controller(args["team"], args["controller"])
                elif key == "set_check_timer":
                    self.check_timer_flag = args["enabled"]
                elif key == "set_check_progress":
                    self.check_progress_flag = args["enabled"]
                elif key == "set_check_goal":
                    self.check_goal_flag = args["enabled"]
                elif key == "set_check_robots_in_penalty_area":
                    self.check_robots_in_penalty_area_flag = args["enabled"]
                elif key == "save_state":
                    self.save_snapshot()
                elif key == "restore_state":
                    self.restore_snapshot()
                elif key == "randomize_ball":
                    x = random.uniform(
                        FIELD_X_LOWER_LIMIT + 0.1, FIELD_X_UPPER_LIMIT - 0.1
                    )
                    y = random.uniform(
                        FIELD_Y_LOWER_LIMIT + 0.1, FIELD_Y_UPPER_LIMIT - 0.1
                    )
                    self.sv.set_ball_position([x, y, BALL_DEPTH])
                elif key == "move_object":
                    self.move_object(
                        args["object"], args["property"], args["value"]
                    )
                elif key == "move_out":
                    self.move_robots_out_of_field()

                # Save the state after ANY message received
                self.saveState()
            except Exception as e:
                print("ERROR:", e)

    def save_snapshot(self):
        data = {}
        data["BALL"] = {
            "translation": self.sv.ball.getField("translation").getSFVec3f(),
            "rotation": self.sv.ball.getField("rotation").getSFRotation(),
            "velocity": self.sv.ball.getVelocity(),
        }

        for robot_name in self.sv.robot_nodes:
            robot = self.sv.robot_nodes[robot_name]
            data[robot_name] = {
                "translation": robot.getField("translation").getSFVec3f(),
                "rotation": robot.getField("rotation").getSFRotation(),
            }
        self.saved_snapshot = data

    def restore_snapshot(self):
        if self.saved_snapshot is None:
            return
        for obj_def in self.saved_snapshot:
            obj = self.sv.getFromDef(obj_def)
            data = self.saved_snapshot[obj_def]
            obj.getField("translation").setSFVec3f(data["translation"])
            obj.getField("rotation").setSFRotation(data["rotation"])
            if "velocity" in data:
                obj.setVelocity(data["velocity"])
            else:
                obj.resetPhysics()

    def move_object(self, object_def, property_name, property_value):
        object = self.sv.getFromDef(object_def)
        if object is None:
            return

        object.setVelocity([0, 0, 0, 0, 0, 0])
        object.resetPhysics()

        if property_name == "a":
            if object_def == "BALL":
                return
            field = object.getField("rotation")
            field_value = [0, 0, 1, math.radians(property_value)]
            field.setSFRotation(field_value)
            self.sv.robot_rotation[object_def] = field_value
        else:
            field = object.getField("translation")
            field_value = field.getSFVec3f()
            if property_name == "x":
                field_value[0] = property_value
            elif property_name == "y":
                field_value[1] = property_value
            field.setSFVec3f(field_value)
            if object_def == "BALL":
                self.ball_translation = field_value
                self.ball_stop = 2
            else:
                self.sv.robot_translation[object_def] = field_value

    def move_robots_out_of_field(self):
        for robot_name in self.sv.robot_nodes:
            yellow = robot_name[0] == "Y"
            index = int(robot_name[1]) - 1

            robot = self.sv.getFromDef(robot_name)
            robot.setVelocity([0, 0, 0, 0, 0, 0])
            robot.resetPhysics()

            # Rotation
            rotation = [0, 0, 1, math.radians(90 * (1 if yellow else -1))]
            robot.getField("rotation").setSFRotation(rotation)
            self.sv.robot_rotation[robot_name] = rotation

            # Translation
            translation = robot.getField("translation").getSFVec3f()
            translation[1] = -0.814 * (1 if yellow else -1)
            translation[0] = (0.283 + (0.1 * index)) * (1 if yellow else -1)
            robot.getField("translation").setSFVec3f(translation)
            self.sv.robot_translation[robot_name] = translation

    def reset_controllers(self):
        for r in self.sv.robot_nodes:
            self.sv.robot_nodes[r].restartController()
        self.log("RESET")

    def set_controller(self, team_name, controller):
        for robot_name in self.sv.robot_nodes:
            if robot_name[0] == team_name:
                robot = self.sv.robot_nodes[robot_name]
                robot.getField("controller").setSFString(controller)

    def update_controllers_list(self):
        controllers = os.listdir(CONTROLLERS_DIR)
        controllers.remove(SUPERVISOR_NAME)
        self.send(
            "update_controllers_list",
            controllers=controllers,
            Y=self.get_current_controller("Y"),
            B=self.get_current_controller("B"),
        )

    def update_flags(self):
        timer_flag = self.check_timer_flag
        progress_flag = self.check_progress_flag
        robots_in_area_flag = self.check_robots_in_penalty_area_flag
        goal_flag = self.check_goal_flag
        self.send(
            "update_flags",
            check_timer=timer_flag,
            check_progress=progress_flag,
            check_robots_in_penalty_area=robots_in_area_flag,
            check_goal=goal_flag,
        )
