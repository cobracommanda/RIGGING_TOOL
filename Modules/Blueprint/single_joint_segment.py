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
        # Gather and return all required information from this modules's control objects
        
        # joint_positions = list of joint positions, from root down the hierarchy
        # joint_orientations = a list or orientations, or a list of axis information (orientJoint and secondaryAxisOrient for joint command)
        #                   These are passed in the following tuple: (orientations, None) or (None, axis_info)
        # joint_rotation_orders = a list of joint rotations orders (integer values gathered with getAttr)
        # joint_preferred_angles = a list of joint preferred angles, optional (can pass None)
        # hook_object = self.find_hook_object_for_lock()
        # root_transform = a bool, either True or False, True = R, T, and S on root joint. False = R only.
        # module_info = (joint_positions, joint_orientations, joint_rotation_orders, joint_preferred_angles, hook_object, root_transform)
        # return module_info
        
        joint_positions = []
        joint_orientation_values = []
        joint_rotation_orders = []
        joints = self.get_joints()
        
        for joint in joints:
            joint_positions.append(cmds.xform(joint, q=True, worldSpace=True, translation=True))
            
        clean_parent = self.module_namespace+":joints_grp"
            
        orientation_info = self.orientation_control_joint_get_orientation(joints[0], clean_parent)
        cmds.delete(orientation_info[1])
        joint_orientation_values.append(orientation_info[0])
        
        joint_orientations = (joint_orientation_values, None)
        joint_rotation_orders.append(cmds.getAttr(joints[0]+".rotateOrder"))
        joint_preferred_angles = None
        hook_object = None
        root_transform = False
        
        module_info = (joint_positions, joint_orientations, joint_rotation_orders, joint_preferred_angles, hook_object, root_transform)
        return module_info
        
        
