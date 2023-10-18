import maya.cmds as cmds
import os
import System.blueprint as blueprint_mod
from importlib import reload

reload(blueprint_mod)

CLASS_NAME = "Single_Joint_Segment"

TITLE = "Single Joint Segment"
DESCRIPTION = "Creates 2 joints, with control for its joint's orientation and rotation order, Ideal use: clavicle bones/shoulder"
ICON = os.environ["RIGGING_TOOL_ROOT"] + "/Icons/_singleJointSeg.xpm"


class Single_Joint_Segment(blueprint_mod.Blueprint):
    def __init__(self, user_specified_name):
        joint_info = [
            ["root_joint", [0.0, 0.0, 0.0]],
            ["end_joint", [4.0, 0.0, 0.0]],
        ]
        
        

        blueprint_mod.Blueprint.__init__(
            self, CLASS_NAME, user_specified_name, joint_info
        )

    def install_custom(self, joints):
        self.create_orientation_control(joints[0], joints[1])
        
    def lock_phase_1(self):
        print("Lock Phase 1")
