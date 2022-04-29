from referee.supervisor import RCJSoccerSupervisor


# HACK(Richo): For some unknown reason, some of the supervisor labels mess up the
# supervisor's robot window. This seems to be a webots bug. The weird thing is that
# some labels (such as the team names, scores, and time) don't present any issue
# (as far as I can tell). So anyway, I made this class as a workaround to avoid
# drawing these messages in the 3D window. Instead, I'm making a separate panel
# in the supervisor window to display these messages. I think this is also better
# because the panel can be scrolled, so we don't need to delete old messages.
class GIRASoccerSupervisor(RCJSoccerSupervisor):
    def draw_event_messages(self, messages):
        pass

    def draw_goal_sign(self, transparency: float = 0.0):
        pass

    def hide_goal_sign(self):
        pass
