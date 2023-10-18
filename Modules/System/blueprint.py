import os
import maya.cmds as cmds
import System.utils as utils


class Blueprint:
    def __init__(self, module_name, user_specified_name, joint_info) -> None:
        self.module_name = module_name
        self.user_specified_name = user_specified_name
        self.module_namespace = self.module_name + "__" + self.user_specified_name
        self.container_name = self.module_namespace + ":module_container"
        self.joint_info = joint_info

    # Method intended for overidding by derived classes
    def install_custom(self, joints):
        print("install_custom() method is not implemented by derived class")

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
        return None

    # BaseClass Methods
    def install(self):
        cmds.namespace(setNamespace=":")
        cmds.namespace(add=self.module_namespace)

        self.joints_grp = cmds.group(
            empty=True, name=self.module_namespace + ":joints_grp"
        )

        self.hierarchy_representation_grp = cmds.group(
            empty=True, name=self.module_namespace + ":hierarchyRepresentation_grp"
        )

        self.orientation_controls_grp = cmds.group(
            empty=True, name=self.module_namespace + ":orientationControls_grp"
        )

        self.module_grp = cmds.group(
            [
                self.joints_grp,
                self.hierarchy_representation_grp,
                self.orientation_controls_grp,
            ],
            name=self.module_namespace + ":module_grp",
        )

        cmds.container(name=self.container_name, addNode=self.module_grp, ihb=True)

        cmds.select(clear=True)

        index = 0
        joints = []

        for joint in self.joint_info:
            joint_name = joint[0]
            joint_pos = joint[1]

            parent_joint = ""
            if index > 0:
                parent_joint = (
                    self.module_namespace + ":" + self.joint_info[index - 1][0]
                )
                cmds.select(parent_joint, replace=True)

            joint_name_full = cmds.joint(
                n=self.module_namespace + ":" + joint_name, p=joint_pos
            )

            joints.append(joint_name_full)

            cmds.setAttr(joint_name_full + ".visibility", 0)

            utils.add_node_to_container(self.container_name, joint_name_full)
            cmds.container(
                self.container_name,
                edit=True,
                publishAndBind=[joint_name_full + ".rotate", joint_name + "_R"],
            )
            cmds.container(
                self.container_name,
                edit=True,
                publishAndBind=[
                    joint_name_full + ".rotateOrder",
                    joint_name + "_rotateOrder",
                ],
            )

            if index > 0:
                cmds.joint(parent_joint, edit=True, orientJoint="xyz", sao="yup")

            index += 1

        cmds.parent(joints[0], self.joints_grp, absolute=True)

        self.initialize_module_transform(self.joint_info[0][1])

        translation_controls = []
        for joint in joints:
            translation_controls.append(self.create_translation_control_at_joint(joint))

        root_joint_point_constraint = cmds.pointConstraint(
            translation_controls[0],
            joints[0],
            maintainOffset=False,
            name=joints[0] + "_pointConstraint",
        )

        utils.add_node_to_container(self.container_name, root_joint_point_constraint)

        # Setup stretchy joint segments
        for index in range(len(joints) - 1):
            self.setup_stretchy_joint_segments(joints[index], joints[index + 1])

        self.install_custom(joints)

        utils.force_scene_update()

        cmds.lockNode(self.container_name, lock=True, lockUnpublished=True)

    def create_translation_control_at_joint(self, joint):
        pos_control_file = (
            os.environ["RIGGING_TOOL_ROOT"]
            + "/ControlObjects/Blueprint/translation_control.ma"
        )
        cmds.file(pos_control_file, i=True)

        container = cmds.rename(
            "translation_control_container", joint + "_translation_control_container"
        )

        utils.add_node_to_container(self.container_name, container)
        for node in cmds.container(container, q=True, nodeList=True):
            cmds.rename(node, joint + "_" + node, ignoreShape=True)

        control = joint + "_translation_control"

        cmds.parent(control, self.module_transform, absolute=True)

        joint_pos = cmds.xform(joint, q=True, worldSpace=True, translation=True)
        cmds.xform(control, worldSpace=True, absolute=True, translation=joint_pos)

        nice_name = utils.strip_leading_namespace(joint)[1]
        attr_name = nice_name + "_T"

        cmds.container(
            container, edit=True, publishAndBind=[control + ".translate", attr_name]
        )
        cmds.container(
            self.container_name,
            edit=True,
            publishAndBind=[container + "." + attr_name, attr_name],
        )

        return control

    def get_translation_control(self, joint_name):
        return joint_name + "_translation_control"

    def setup_stretchy_joint_segments(self, parent_joint, child_joint):
        parent_translation_control = self.get_translation_control(parent_joint)
        child_translation_control = self.get_translation_control(child_joint)

        pole_vector_locator = cmds.spaceLocator(
            n=parent_translation_control + "_poleVectorLocator"
        )[0]
        pole_vector_locator_grp = cmds.group(
            pole_vector_locator, n=pole_vector_locator + "_parentConstraintGrp"
        )
        cmds.parent(pole_vector_locator_grp, self.module_grp, absolute=True)
        parent_constraint = cmds.parentConstraint(
            parent_translation_control, pole_vector_locator_grp, maintainOffset=False
        )[0]
        cmds.setAttr(pole_vector_locator + ".visibility", 0)

        cmds.setAttr(pole_vector_locator + ".ty", -0.5)

        ik_nodes = utils.basic_stretchy_ik(
            parent_joint,
            child_joint,
            container=self.container_name,
            lock_minimum_length=False,
            pole_vector_object=pole_vector_locator,
            scale_correction_attribute=None,
        )

        ik_handle = ik_nodes["ik_handle"]
        root_locator = ik_nodes["root_locator"]
        end_locator = ik_nodes["end_locator"]

        child_point_constraint = cmds.pointConstraint(
            child_translation_control,
            end_locator,
            maintainOffset=False,
            n=end_locator + "_pointConstraint",
        )[0]

        utils.add_node_to_container(
            self.container_name,
            [
                pole_vector_locator_grp,
                parent_constraint,
                child_point_constraint,
            ],
            ihb=True,
        )

        for node in [ik_handle, root_locator, end_locator]:
            cmds.parent(node, self.joints_grp, absolute=True)
            cmds.setAttr(node + ".visibility", 0)

        self.create_hierarchy_representation(parent_joint, child_joint)

    def create_hierarchy_representation(self, parent_joint, child_joint):
        nodes = self.create_stretchy_object(
            "/ControlObjects/Blueprint/hierarchy_representation.ma",
            "hierarchy_representation_container",
            "hierarchy_representation",
            parent_joint,
            child_joint,
        )

        constrained_grp = nodes[2]

        cmds.parent(constrained_grp, self.hierarchy_representation_grp, relative=True)

    def create_stretchy_object(
        self,
        object_relative_file_path,
        object_container_name,
        object_name,
        parent_joint,
        child_joint,
    ):
        object_file = os.environ["RIGGING_TOOL_ROOT"] + object_relative_file_path

        cmds.file(object_file, i=True)
        object_container = cmds.rename(
            object_container_name, parent_joint + "_" + object_container_name
        )

        for node in cmds.container(object_container, q=True, nodeList=True):
            cmds.rename(node, parent_joint + "_" + node, ignoreShape=True)

        object = parent_joint + "_" + object_name

        constrained_grp = cmds.group(empty=True, name=object + "_parentConstraint_grp")
        cmds.parent(object, constrained_grp, absolute=True)

        parent_constraint = cmds.parentConstraint(
            parent_joint, constrained_grp, maintainOffset=False
        )[0]
        cmds.connectAttr(child_joint + ".translateX", constrained_grp + ".scaleX")

        scale_constraint = cmds.scaleConstraint(
            self.module_transform, constrained_grp, skip=["x"], maintainOffset=False
        )[0]

        utils.add_node_to_container(
            object_container,
            [constrained_grp, parent_constraint, scale_constraint],
            ihb=True,
        )
        utils.add_node_to_container(self.container_name, object_container)

        return (object_container, object, constrained_grp)

    def initialize_module_transform(self, root_pos):
        control_grp_file = (
            os.environ["RIGGING_TOOL_ROOT"]
            + "/ControlObjects/Blueprint/controlGroup_control.ma"
        )
        cmds.file(control_grp_file, i=True)

        self.module_transform = cmds.rename(
            "controlGroup_control", self.module_namespace + ":module_transform"
        )

        cmds.xform(
            self.module_transform, worldSpace=True, absolute=True, translation=root_pos
        )

        utils.add_node_to_container(
            self.container_name, self.module_transform, ihb=True
        )

        # Setup global scaling
        cmds.connectAttr(
            self.module_transform + ".scaleY", self.module_transform + ".scaleX"
        )
        cmds.connectAttr(
            self.module_transform + ".scaleY", self.module_transform + ".scaleZ"
        )

        cmds.aliasAttr("globalScale", self.module_transform + ".scaleY")
        cmds.container(
            self.container_name,
            edit=True,
            publishAndBind=[self.module_transform + ".translate", "moduleTransform_T"],
        )
        cmds.container(
            self.container_name,
            edit=True,
            publishAndBind=[self.module_transform + ".rotate", "moduleTransform_R"],
        )
        cmds.container(
            self.container_name,
            edit=True,
            publishAndBind=[
                self.module_transform + ".globalScale",
                "moduleTransform_globalScale",
            ],
        )

    def delete_hierarchy_representation(self, parent_joint):
        hierarchy_container = parent_joint + "_hierarchy_representation_container"
        cmds.delete(hierarchy_container)

    def create_orientation_control(self, parent_joint, child_joint):
        self.delete_hierarchy_representation(parent_joint)

        nodes = self.create_stretchy_object(
            "/ControlObjects/Blueprint/orientation_control.ma",
            "orientation_control_container",
            "orientation_control",
            parent_joint,
            child_joint,
        )

        orientation_container = nodes[0]
        orientation_control = nodes[1]
        constrained_grp = nodes[2]

        cmds.parent(constrained_grp, self.orientation_controls_grp, relative=True)
        parent_joint_without_namespace = utils.strip_all_namespaces(parent_joint)[1]

        attr_name = parent_joint_without_namespace + "_orientation"
        cmds.container(
            orientation_container,
            edit=True,
            publishAndBind=[orientation_control + ".rotateX", attr_name],
        )
        cmds.container(
            self.container_name,
            edit=True,
            publishAndBind=[orientation_container + "." + attr_name, attr_name],
        )

        return orientation_control

    def get_joints(self):
        joint_basename = self.module_namespace + ":"
        joints = []

        for joint_inf in self.joint_info:
            joints.append(joint_basename + joint_inf[0])

        return joints

    def get_orientation_control(self, joint_name):
        return joint_name + "_orientation_control"

    def orientation_control_joint_get_orientation(self, joint, clean_parent):
        new_clean_parent = cmds.duplicate(joint, parentOnly=True)[0]

        if not clean_parent in cmds.listRelatives(new_clean_parent, parent=True):
            cmds.parent(new_clean_parent, clean_parent, absolute=True)

        cmds.makeIdentity(
            new_clean_parent, apply=True, rotate=True, scale=False, translate=False
        )

        orientation_control = self.get_orientation_control(joint)
        cmds.setAttr(
            new_clean_parent + ".rotateX",
            cmds.getAttr(orientation_control + ".rotateX"),
        )

        cmds.makeIdentity(
            new_clean_parent, apply=True, rotate=True, scale=False, translate=False
        )

        orient_x = cmds.getAttr(new_clean_parent + ".jointOrientX")
        orient_y = cmds.getAttr(new_clean_parent + ".jointOrientY")
        orient_z = cmds.getAttr(new_clean_parent + ".jointOrientZ")

        orientation_values = (orient_x, orient_y, orient_z)
        return (orientation_values, new_clean_parent)

    def lock_phase_2(self, module_info):
        joint_positions = module_info[0]
        num_joints = len(joint_positions)

        joint_orientations = module_info[1]
        orient_with_axis = False
        pure_orientations = False

        if joint_orientations[0] == None:
            orient_with_axis = True
            joint_orientations = joint_orientations[1]
        else:
            pure_orientations = True
            joint_orientations = joint_orientations[0]

        num_orientations = len(joint_orientations)

        joint_rotation_orders = module_info[2]
        num_rotation_orders = len(joint_rotation_orders)

        joint_preferred_angles = module_info[3]
        num_preferred_angles = 0
        if joint_preferred_angles != None:
            num_preferred_angles = len(joint_preferred_angles)

        # hook_object = module_info[4]
        root_transform = module_info[5]

        # Delete our blueprint controls
        cmds.lockNode(self.container_name, lock=False, lockUnpublished=False)
        cmds.delete(self.container_name)
        cmds.namespace(setNamespace=":")

        joint_radius = 1
        if num_joints == 1:
            joint_radius = 1.5

        new_joints = []
        for i in range(num_joints):
            new_joint = ""
            cmds.select(clear=True)

            if orient_with_axis:
                print("orient_with_axis")
            else:
                if i != 0:
                    cmds.select(new_joints[i - 1])

                joint_orientation = [0.0, 0.0, 0.0]
                if i < num_orientations:
                    joint_orientation = [
                        joint_orientations[i][0],
                        joint_orientations[i][1],
                        joint_orientations[i][2],
                    ]

                new_joint = cmds.joint(
                    n=self.module_namespace + ":blueprint_" + self.joint_info[i][0],
                    p=joint_positions[i],
                    orientation=joint_orientation,
                    rotationOrder="xyz",
                    radius=joint_radius,
                )

                new_joints.append(new_joint)

                if i < num_rotation_orders:
                    cmds.setAttr(
                        new_joint + ".rotateOrder", int(joint_rotation_orders[i])
                    )

                if i < num_preferred_angles:
                    cmds.setAttr(
                        new_joint + ".preferredAngleX",
                        int(joint_preferred_angles[i][0]),
                    )
                    cmds.setAttr(
                        new_joint + ".preferredAngleY",
                        int(joint_preferred_angles[i][1]),
                    )
                    cmds.setAttr(
                        new_joint + ".preferredAngleZ",
                        int(joint_preferred_angles[i][2]),
                    )

                cmds.setAttr(new_joint + ".segmentScaleCompensate", 0)

            blueprint_grp = cmds.group(
                empty=True, name=self.module_namespace + ":blueprint_joints_grp"
            )
            cmds.parent(new_joints[0], blueprint_grp, absolute=True)

            creation_pose_grp_nodes = cmds.duplicate(
                blueprint_grp,
                name=self.module_namespace + ":creationPose_joints_grp",
                renameChildren=True,
            )
            
            creation_pose_grp = creation_pose_grp_nodes[0]

            
            creation_pose_grp_nodes.pop(0)
  
            i = 0
            for node in creation_pose_grp_nodes:
                renamed_node = cmds.rename(
                    node,
                    self.module_namespace + ":creationPose_" + self.joint_info[i][0],
                )
                cmds.setAttr(renamed_node + ".visibility", 0)
                i += 1

            cmds.select(blueprint_grp, replace=True)
            cmds.addAttr(
                at="bool",  defaultValue=0, longName="controlModulesInstalled", k=False
            )
            setting_locator = cmds.spaceLocator(n=self.module_namespace + ":SETTINGS")[
                0
            ]
            cmds.setAttr(setting_locator + ".visibility", 0)
            cmds.select(setting_locator, replace=True)
            cmds.addAttr(at="enum", ln="activeModule", en="None:", k=False)
            cmds.addAttr(at="float", ln="creationPoseWeight", defaultValue=1, k=False)
            
            
            

            
            
