import os
import maya.cmds as cmds
import System.utils as utils


class Blueprint:
    def __init__(
        self, module_name, user_specified_name, joint_info, hook_obj_in
    ) -> None:
        self.module_name = module_name
        self.user_specified_name = user_specified_name
        self.module_namespace = self.module_name + "__" + self.user_specified_name
        self.container_name = self.module_namespace + ":module_container"
        self.joint_info = joint_info

        self.hook_obj = None
        if hook_obj_in != None:
            partition_info = hook_obj_in.rpartition("_translation_control")
            if partition_info[1] != "" and partition_info[2] == "":
                self.hook_obj = hook_obj_in

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

    def UI_custom(self):
        temp = 1

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

        self.initialize_hook(translation_controls[0])

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
        num_rotations_orders = len(joint_rotation_orders)
        joint_preferred_angles = module_info[3]
        num_preferred_angles = 0
        if joint_preferred_angles != None:
            num_preferred_angles = len(joint_preferred_angles)

        # hook_object = module_info[4]
        root_transform = module_info[5]

        # Delete blueprint controls
        cmds.lockNode(self.container_name, lock=False, lockUnpublished=False)
        cmds.delete(self.container_name)
        cmds.namespace(setNamespace=":")

        joint_radius = 1
        if num_joints == 1:
            joint_radius = 1.5

        # Initialize as an empty list
        new_joints = []

        for i in range(num_joints):
            cmds.select(clear=True)

            if orient_with_axis:
                new_joint = cmds.joint(
                    n=self.module_namespace + ":blueprint_" + self.joint_info[i][0],
                    p=joint_positions[i],
                    rotationOrder="xyz",
                    radius=joint_radius,
                )

                if i != 0:
                    cmds.parent(new_joint, new_joints[i - 1], absolute=True)
                    offset_index = i - 1
                    if offset_index < num_orientations:
                        cmds.joint(
                            new_joints[offset_index],
                            edit=True,
                            oj=joint_orientations[offset_index][0],
                            sao=joint_orientations[offset_index][1],
                        )

                        cmds.makeIdentity(new_joint, rotate=True, apply=True)

            else:
                if i != 0:
                    cmds.select(new_joints[i - 1])

                joint_orientation = [0.0, 0.0, 0.0]
                if i < num_orientations:
                    # Assign the orientation values
                    joint_orientation = list(joint_orientations[i])

                new_joint = cmds.joint(
                    n=self.module_namespace + ":blueprint_" + self.joint_info[i][0],
                    p=joint_positions[i],
                    orientation=joint_orientation,
                    rotationOrder="xyz",
                    radius=joint_radius,
                )

            new_joints.append(new_joint)

            if i < num_rotations_orders:
                cmds.setAttr(new_joint + ".rotateOrder", int(joint_rotation_orders[i]))

            if i < num_preferred_angles:
                cmds.setAttr(
                    new_joint + ".preferredAngleX", int(joint_rotation_orders[i][0])
                )
                cmds.setAttr(
                    new_joint + ".preferredAngleY", int(joint_rotation_orders[i][1])
                )
                cmds.setAttr(
                    new_joint + ".preferredAngleZ", int(joint_rotation_orders[i][2])
                )

            cmds.setAttr(new_joint + ".segmentScaleCompensate", 0)

        blueprint_grp = cmds.group(
            empty=True, name=self.module_namespace + ":blueprint_joint_grp"
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
            rename_node = cmds.rename(
                node, self.module_namespace + ":creationPose_" + self.joint_info[i][0]
            )
            cmds.setAttr(rename_node + ".visibility", 0)
            i += 1

        cmds.select(blueprint_grp, replace=True)
        cmds.addAttr(
            at="bool", defaultValue=0, longName="controlModulesInstalled", k=False
        )

        hook_grp = cmds.group(empty=True, n=f"{self.module_namespace}:HOOK_IN")
        for obj in [blueprint_grp, creation_pose_grp]:
            cmds.parent(obj, hook_grp)

        setting_locator = cmds.spaceLocator(n=self.module_namespace + ":SETTINGS")[0]
        cmds.setAttr(setting_locator + ".visibility", 0)

        cmds.select(setting_locator, replace=True)
        cmds.addAttr(at="enum", ln="activeModule", en="None:", k=False)
        cmds.addAttr(at="float", ln="creationPoseWeight", defaultValue=1, k=False)

        i = 0
        utility_nodes = []

        for joint in new_joints:
            if i < (num_joints - 1) or num_joints == 1:
                add_node = cmds.shadingNode(
                    "plusMinusAverage", n=joint + "_addRotations", asUtility=True
                )
                cmds.connectAttr(add_node + ".output3D", joint + ".rotate", force=True)
                utility_nodes.append(add_node)

                dummy_rotations_multiply = cmds.shadingNode(
                    "multiplyDivide",
                    n=joint + "_dummyRotationsMultiply",
                    asUtility=True,
                )
                cmds.connectAttr(
                    dummy_rotations_multiply + ".output",
                    add_node + ".input3D[0]",
                    force=True,
                )
                utility_nodes.append(dummy_rotations_multiply)

            if i > 0:
                original_tx = cmds.getAttr(joint + ".tx")
                add_tx_node = cmds.shadingNode(
                    "plusMinusAverage", n=joint + "_addTx", asUtility=True
                )
                cmds.connectAttr(
                    add_tx_node + ".output1D", joint + ".translateX", force=True
                )
                utility_nodes.append(add_tx_node)

                original_tx_multiply = cmds.shadingNode(
                    "multiplyDivide", n=joint + "_original_Tx", asUtility=True
                )

                cmds.setAttr(original_tx_multiply + ".input1X", original_tx, lock=True)
                cmds.connectAttr(
                    setting_locator + ".creationPoseWeight",
                    original_tx_multiply + ".input2X",
                    force=True,
                )

                cmds.connectAttr(
                    original_tx_multiply + ".outputX",
                    add_tx_node + ".input1D[0]",
                    force=True,
                )
                utility_nodes.append(original_tx_multiply)
            else:
                if root_transform:
                    original_translates = cmds.getAttr(joint + ".translate")[0]
                    add_translate_node = cmds.shadingNode(
                        "plusMinusAverage", n=joint + "_addTranslate", asUtility=True
                    )
                    cmds.connectAttr(
                        add_translate_node + ".output3D",
                        joint + ".translate",
                        force=True,
                    )
                    utility_nodes.append(add_translate_node)

                    original_translate_multiply = cmds.shadingNode(
                        "multiplyDivide",
                        n=joint + "_original_Translate",
                        asUtility=True,
                    )
                    cmds.setAttr(
                        original_translate_multiply + ".input1",
                        original_translates[0],
                        original_translates[1],
                        original_translates[2],
                        type="double3",
                    )

                    for attr in ["X", "Y", "Z"]:
                        cmds.connectAttr(
                            setting_locator + ".creationPoseWeight",
                            original_translate_multiply + ".input2" + attr,
                        )
                    cmds.connectAttr(
                        original_translate_multiply + ".output",
                        add_translate_node + ".input3D[0]",
                        force=True,
                    )
                    utility_nodes.append(original_translate_multiply)

                    # Scale
                    original_scales = cmds.getAttr(joint + ".scale")[0]
                    add_scale_node = cmds.shadingNode(
                        "plusMinusAverage", n=joint + "_addScale", asUtility=True
                    )
                    cmds.connectAttr(
                        add_scale_node + ".output3D", joint + ".scale", force=True
                    )
                    utility_nodes.append(add_scale_node)

                    original_scale_multiply = cmds.shadingNode(
                        "multiplyDivide", n=joint + "_original_Scale", asUtility=True
                    )
                    cmds.setAttr(
                        original_scale_multiply + ".input1",
                        original_scales[0],
                        original_scales[1],
                        original_scales[2],
                        type="double3",
                    )

                    for attr in ["X", "Y", "Z"]:
                        cmds.connectAttr(
                            setting_locator + ".creationPoseWeight",
                            original_scale_multiply + ".input2" + attr,
                        )
                    cmds.connectAttr(
                        original_scale_multiply + ".output",
                        add_scale_node + ".input3D[0]",
                        force=True,
                    )
                    utility_nodes.append(original_scale_multiply)

            i += 1

        blueprint_nodes = utility_nodes
        blueprint_nodes.append(blueprint_grp)
        blueprint_nodes.append(creation_pose_grp)

        blueprint_container = cmds.container(
            n=self.module_namespace + ":blueprint_container"
        )
        utils.add_node_to_container(blueprint_container, blueprint_nodes, ihb=True)

        module_grp = cmds.group(empty=True, name=self.module_namespace + ":module_grp")
        for obj in [hook_grp, setting_locator]:
            cmds.parent(obj, module_grp, absolute=True)

        module_container = cmds.container(n=self.module_namespace + ":module_container")
        utils.add_node_to_container(
            module_container,
            [module_grp, hook_grp, setting_locator, blueprint_container],
            includeShapes=True,
        )

        cmds.container(
            module_container,
            edit=True,
            publishAndBind=[setting_locator + ".activeModule", "activeModule"],
        )
        cmds.container(
            module_container,
            edit=True,
            publishAndBind=[
                setting_locator + ".creationPoseWeight",
                "creationPoseWeight",
            ],
        )

        cmds.select(module_grp)
        cmds.addAttr(at="float", longName="hierarchicalScale")
        cmds.connectAttr(f"{hook_grp}.scaleY", f"{module_grp}.hierarchicalScale")

    def UI(self, blueprint_ui_instance, parent_column_layout):
        self.blueprint_UI_instance = blueprint_ui_instance
        self.parent_column_layout = parent_column_layout
        self.UI_custom()

    def create_rotation_order_ui_control(self, joint):
        joint_name = utils.strip_all_namespaces(joint)[1]

        # Check if the joint exists
        if not cmds.objExists(joint):
            return

        try:
            attr_control_group = cmds.attrControlGrp(
                attribute=f"{joint}.rotateOrder", label=joint_name
            )
        except Exception as e:
            print(
                f"Error accessing rotateOrder attribute for joint {joint}. Error: {e}"
            )

    def delete(self):
        cmds.lockNode(self.container_name, lock=False, lockUnpublished=False)

        valid_module_info = utils.find_all_module_names("/Modules/Blueprint")
        valid_modules = valid_module_info[0]
        valid_module_names = valid_module_info[1]

        hooked_modules = set()
        for joint_inf in self.joint_info:
            joint = joint_inf[0]
            translation_control = self.get_translation_control(
                f"{self.module_namespace}:{joint}"
            )

            connections = cmds.listConnections(translation_control)

            for connection in connections:
                module_instance = utils.strip_leading_namespace(connection)

                if module_instance != None:
                    split_string = module_instance[0].partition("__")
                    if (
                        module_instance[0] != self.module_namespace
                        and split_string[0] in valid_module_names
                    ):
                        index = valid_module_names.index(split_string[0])
                        hooked_modules.add((valid_modules[index], split_string[2]))

        for module in hooked_modules:
            mod = __import__(f"Blueprint.{module[0]}", {}, {}, [module[0]])
            module_class = getattr(mod, mod.CLASS_NAME)
            module_inst = module_class(module[1], None)
            module_inst.rehook(None)

        cmds.delete(self.container_name)

        cmds.namespace(setNamespace=":")
        cmds.namespace(removeNamespace=self.module_namespace)

    def rename_module_instance(self, new_name):
        if new_name == self.user_specified_name:
            return True

        if utils.does_blueprint_user_specified_name_exist(new_name):
            cmds.confirmDialog(
                title="Name Conflict",
                message=f"Name \{new_name}\ already exist, aborting rename",
                button=["Accept"],
                defaultButton="Accept",
            )
            return False
        else:
            new_namespace = f"{self.module_name}__{new_name}"
            cmds.lockNode(self.container_name, lock=False, lockUnpublished=False)
            cmds.namespace(setNamespace=":")
            cmds.namespace(add=new_namespace)
            cmds.namespace(setNamespace=":")
            cmds.namespace(moveNamespace=[self.module_namespace, new_namespace])
            cmds.namespace(removeNamespace=self.module_namespace)

            self.module_namespace = new_namespace
            self.container_name = f"{self.module_namespace}:module_container"
            cmds.lockNode(self.container_name, lock=True, lockUnpublished=True)
            return True

    def initialize_hook(self, root_translation_control):
        unhooked_locator = cmds.spaceLocator(
            name=f"{self.module_namespace}:unhookedTarget"
        )[0]
        cmds.pointConstraint(
            root_translation_control, unhooked_locator, offset=[0, 0.001, 0]
        )
        cmds.setAttr(f"{unhooked_locator}.visibility", 0)

        if self.hook_obj == None:
            self.hook_obj = unhooked_locator

        root_pos = cmds.xform(
            root_translation_control, q=True, worldSpace=True, translation=True
        )
        target_pos = cmds.xform(
            self.hook_obj, q=True, worldSpace=True, translation=True
        )

        cmds.select(clear=True)

        root_joint_without_namespace = "hook_root_joint"
        root_joint = cmds.joint(
            n=f"{self.module_namespace}:{root_joint_without_namespace}", p=root_pos
        )
        cmds.setAttr(f"{root_joint}.visibility", 0)

        target_joint_without_namespace = "hook_target_joint"
        target_joint = cmds.joint(
            n=f"{self.module_namespace}:{target_joint_without_namespace}", p=target_pos
        )
        cmds.setAttr(f"{target_joint}.visibility", 0)

        cmds.joint(root_joint, edit=True, orientJoint="xyz", sao="yup")

        hook_group = cmds.group(
            [root_joint, unhooked_locator],
            n=f"{self.module_namespace}:hook_grp",
            parent=self.module_grp,
        )
        hook_container = cmds.container(name=f"{self.module_namespace}:hook_container")
        utils.add_node_to_container(hook_container, hook_group, ihb=True)
        utils.add_node_to_container(self.container_name, hook_container)

        for joint in [root_joint, target_joint]:
            joint_name = utils.strip_all_namespaces(joint)[1]
            cmds.container(
                hook_container,
                edit=True,
                publishAndBind=[f"{joint}.rotate", f"{joint_name}_R"],
            )

        ik_nodes = utils.basic_stretchy_ik(
            root_joint, target_joint, hook_container, lock_minimum_length=False
        )
        ik_handle = ik_nodes["ik_handle"]
        root_locator = ik_nodes["root_locator"]
        end_locator = ik_nodes["end_locator"]
        pole_vector_locator = ik_nodes["pole_vector_object"]

        root_point_constraint = cmds.pointConstraint(
            root_translation_control,
            root_joint,
            maintainOffset=False,
            n=f"{root_joint}_pointConstraint",
        )[0]
        target_point_constraint = cmds.pointConstraint(
            self.hook_obj,
            end_locator,
            maintainOffset=False,
            n=f"{self.module_namespace}:hook_pointConstraint",
        )[0]

        utils.add_node_to_container(
            hook_container, [root_point_constraint, target_point_constraint]
        )

        for node in [ik_handle, root_locator, end_locator, pole_vector_locator]:
            cmds.parent(node, hook_group, absolute=True)
            cmds.setAttr(f"{node}.visibility", 0)

        object_nodes = self.create_stretchy_object(
            "/ControlObjects/Blueprint/hook_representation.ma",
            "hook_representation_container",
            "hook_representation",
            root_joint,
            target_joint,
        )
        constraint_grp = object_nodes[2]
        cmds.parent(constraint_grp, hook_group, absolute=True)
        hook_representation_container = object_nodes[0]

        cmds.container(
            self.container_name, edit=True, removeNode=hook_representation_container
        )
        utils.add_node_to_container(hook_container, hook_representation_container)

    def rehook(self, new_hook_object):
        old_hook_obj = self.find_hook_obj()
        self.hook_obj = f"{self.module_namespace}:unhookedTarget"

        if new_hook_object != None:
            if new_hook_object.find("_translation_control") != 1:
                split_string = new_hook_object.split("_translation_control")
                if split_string[1] == "":
                    if (
                        utils.strip_leading_namespace(new_hook_object)[0]
                        != self.module_namespace
                    ):
                        self.hook_obj = new_hook_object

        if self.hook_obj == old_hook_obj:
            return
        
        self.unconstrain_root_from_hook()

        cmds.lockNode(self.container_name, lock=False, lockUnpublished=False)
        hook_constraint = f"{self.module_namespace}:hook_pointConstraint"

        cmds.connectAttr(
            f"{self.hook_obj}.parentMatrix[0]",
            f"{hook_constraint}.target[0].targetParentMatrix",
            force=True,
        )
        cmds.connectAttr(
            f"{self.hook_obj}.translate",
            f"{hook_constraint}.target[0].targetTranslate",
            force=True,
        )
        cmds.connectAttr(
            f"{self.hook_obj}.rotatePivot",
            f"{hook_constraint}.target[0].targetRotatePivot",
            force=True,
        )
        cmds.connectAttr(
            f"{self.hook_obj}.rotatePivotTranslate",
            f"{hook_constraint}.target[0].targetRotateTranslate",
            force=True,
        )

        cmds.lockNode(self.container_name, lock=True, lockUnpublished=True)

    def find_hook_obj(self):
        hook_constraint = f"{self.module_namespace}:hook_pointConstraint"
        source_attr = cmds.connectionInfo(
            f"{hook_constraint}.target[0].targetParentMatrix",
            sourceFromDestination=True,
        )
        source_node = str(source_attr.rpartition(".")[0])
        return source_node

    def find_hook_obj_for_lock(self):
        hook_object = self.find_hook_obj()

        if hook_object == f"{self.module_namespace}:unhookedTarget":
            hook_object = None
        else:
            self.rehook(None)

        return hook_object

    def lock_phase3(self, hook_object):
        module_container = f"{self.module_namespace}:module_container"

        if hook_object != None:
            hook_object_module_node = utils.strip_leading_namespace(hook_object)
            hook_obj_module = hook_object_module_node[0]
            hook_obj_joint = hook_object_module_node[1].split("_translation_control")[0]

            hook_obj = f"{hook_obj_module}:blueprint_{hook_obj_joint}"
            parent_constraint = cmds.parentConstraint(
                hook_obj,
                f"{self.module_namespace}:HOOK_IN",
                maintainOffset=True,
                n=f"{self.module_namespace}:hook_parent_constraint",
            )[0]
            scale_constraint = cmds.scaleConstraint(
                hook_obj,
                f"{self.module_namespace}:HOOK_IN",
                maintainOffset=True,
                n=f"{self.module_namespace}:hook_scale_constraint",
            )[0]

            utils.add_node_to_container(
                module_container, [parent_constraint, scale_constraint]
            )

        cmds.lockNode(module_container, lock=True, lockUnpublished=True)

    def snap_root_to_hook(self):
        root_control = self.get_translation_control(
            f"{self.module_namespace}:{self.joint_info[0][0]}"
        )
        hook_object = self.find_hook_obj()

        if hook_object == f"{self.module_namespace}:unhookedTarget":
            return

        hook_object_pos = cmds.xform(
            hook_object, q=True, worldSpace=True, translation=True
        )
        cmds.xform(
            root_control, worldSpace=True, absolute=True, translation=hook_object_pos
        )

    def constrain_root_to_hook(self):
        root_control = self.get_translation_control(
            f"{self.module_namespace}:{self.joint_info[0][0]}"
        )
        hook_object = self.find_hook_obj()

        if hook_object == f"{self.module_namespace}:unhookedTarget":
            return

        cmds.lockNode(self.container_name, lock=False, lockUnpublished=False)

        cmds.pointConstraint(
            hook_object,
            root_control,
            maintainOffset=False,
            n=f"{root_control}_hookConstraint",
        )
        cmds.setAttr(f"{root_control}.translate", l=True)
        cmds.setAttr(f"{root_control}.visibility", l=False)
        cmds.setAttr(f"{root_control}.visibility", 0)
        cmds.setAttr(f"{root_control}.visibility", l=True)

        cmds.select(clear=True)

        cmds.lockNode(self.container_name, lock=True, lockUnpublished=True)

    def unconstrain_root_from_hook(self):
        cmds.lockNode(self.container_name, lock=False, lockUnpublished=False)

        root_control = self.get_translation_control(
            f"{self.module_namespace}:{self.joint_info[0][0]}"
        )
        root_control_hook_constraint = f"{root_control}_hookConstraint"

        if cmds.objExists(root_control_hook_constraint):
            cmds.delete(root_control_hook_constraint)

            cmds.setAttr(f"{root_control}.translate", l=False)
            cmds.setAttr(f"{root_control}.visibility", l=False)
            cmds.setAttr(f"{root_control}.visibility", 1)
            cmds.setAttr(f"{root_control}.visibility", l=True)
            
            cmds.select(root_control, replace=True)
            cmds.setToolTo("moveSuperContext")

        cmds.lockNode(self.container_name, lock=True, lockUnpublished=True)
        
    def is_root_constrained(self):
        root_control = self.get_translation_control(
            f"{self.module_namespace}:{self.joint_info[0][0]}"
        )
        root_control_hook_constraint = f"{root_control}_hookConstraint"
        
        return cmds.objExists(root_control_hook_constraint)
        
