import maya.cmds as cmds
from functools import partial
from importlib import reload
import System.utils as utils

reload(utils)


class Blueprint_UI:
    def __init__(self) -> None:
        self.UI_elements = {}

        if cmds.window("blueprint_UI_window", exists=True):
            cmds.deleteUI("blueprint_UI_window")

        window_width = 400
        window_height = 598

        self.UI_elements["window"] = cmds.window(
            "blueprint_UI_window",
            width=window_width,
            height=window_height,
            title="Blueprint Module UI",
            sizeable=False,
        )

        self.UI_elements["top_level_column"] = cmds.columnLayout(
            adjustableColumn=True, columnAlign="center"
        )

        # Setup tabs
        tab_height = 500
        self.UI_elements["tabs"] = cmds.tabLayout(
            height=tab_height, innerMarginWidth=5, innerMarginHeight=5
        )
        tab_width = cmds.tabLayout(self.UI_elements["tabs"], q=True, width=True)
        self.scroll_width = tab_height - 120
        self.initialize_module_tab(tab_height, tab_width)
        cmds.tabLayout(
            self.UI_elements["tabs"], edit=True, tabLabelIndex=([1, "Modules"])
        )

        cmds.setParent(self.UI_elements["top_level_column"])
        self.UI_elements["lock_publish_column"] = cmds.columnLayout(
            adj=True, columnAlign="center", rs=3
        )

        cmds.separator()
        self.UI_elements["lock_btn"] = cmds.button(label="Lock", c=self.lock)
        cmds.separator()
        self.UI_elements["publish_btn"] = cmds.button(label="Publish")
        cmds.separator()
        cmds.showWindow(self.UI_elements["window"])

    def initialize_module_tab(self, tab_height, tab_width):
        scroll_height = tab_height - 200

        self.UI_elements["module_column"] = cmds.columnLayout(adj=True, rs=3)

        self.UI_elements["module_frame_layout"] = cmds.frameLayout(
            height=scroll_height,
            collapsable=False,
            borderVisible=False,
            labelVisible=False,
        )

        self.UI_elements["module_list_scroll"] = cmds.scrollLayout(hst=0)

        self.UI_elements["module_list_column"] = cmds.columnLayout(
            columnWidth=self.scroll_width, adj=True, rs=2
        )

        # First separator
        cmds.separator()

        for module in utils.find_all_modules("Modules/Blueprint"):
            self.create_module_install_button(module)
        cmds.setParent(self.UI_elements["module_list_column"])
        cmds.separator()

        cmds.setParent(self.UI_elements["module_column"])
        cmds.separator()

        # Create the row layout for the module name
        self.UI_elements["module_name_row"] = cmds.rowLayout(
            nc=2,
            columnAttach=(1, "right", 0),
            columnWidth=[1, 80],
            adjustableColumn=2,  # Make the second column (text field) adjustable
        )

        cmds.text(label="Module Name :")
        self.UI_elements["module_name"] = cmds.textField(
            enable=False, alwaysInvokeEnterCommandOnReturn=True
        )
        cmds.setParent(self.UI_elements["module_column"])

        # Adjust column width based on total width minus padding.
        column_width = 138 - 20 / 3

        # Create button columns
        self.UI_elements["module_button_row_column"] = cmds.rowColumnLayout(
            numberOfColumns=3,
            ro=[(1, "both", 2), (2, "both", 2), (3, "both", 2)],
            columnAttach=[(1, "both", 3), (2, "both", 3), (3, "both", 3)],
            columnWidth=[(1, column_width), (2, column_width), (3, column_width)],
        )

        self.UI_elements["rehook_btn"] = cmds.button(enable=False, label="Re-hook")
        self.UI_elements["snap_root_btn"] = cmds.button(
            enable=False, label="Snap Root > Hook"
        )
        self.UI_elements["constrain_root_btn"] = cmds.button(
            enable=False, label="Constrain Root > Hook"
        )

        self.UI_elements["group_selected_btn"] = cmds.button(label="Group Selected")
        self.UI_elements["ungroup_btn"] = cmds.button(enable=False, label="Ungroup")
        self.UI_elements["mirror_module_btn"] = cmds.button(
            enable=False, label="Mirror Module"
        )

        cmds.button(enable=False, label="")
        self.UI_elements["delete_btn"] = cmds.button(enable=False, label="Delete")
        self.UI_elements["symmetry_move_checkbox"] = cmds.checkBox(
            enable=True, label="Symmetry Move"
        )

        cmds.setParent(self.UI_elements["module_column"])
        cmds.separator()

    def create_module_install_button(self, module):
        mod = __import__("Blueprint." + module, {}, {}, [module])
        reload(mod)

        title = mod.TITLE
        description = mod.DESCRIPTION
        icon = mod.ICON

        # Create UI
        button_size = 64
        row = cmds.rowLayout(
            numberOfColumns=2,
            columnWidth=([1, button_size]),
            adjustableColumn=2,
            columnAttach=([1, "both", 0], [2, "both", 5]),
        )
        self.UI_elements["module_button_" + module] = cmds.symbolButton(
            width=button_size,
            height=button_size,
            image=icon,
            command=partial(self.install_module, module),
        )

        text_column = cmds.columnLayout(columnAlign="center")
        cmds.text(align="left", width=self.scroll_width - button_size - 16, label=title)

        cmds.scrollField(
            text=description,
            editable=False,
            width=self.scroll_width - button_size - 16,
            height=64,
            wordWrap=True,
        )

    def install_module(self, module, *args):
        basename = "instance_"
        cmds.namespace(setNamespace=":")
        namespaces = cmds.namespaceInfo(listOnlyNamespaces=True)

        for i in range(len(namespaces)):
            if namespaces[i].find("__") != -1:
                namespaces[i] = namespaces[i].partition("__")[2]

        new_suffix = utils.find_highest_trailing_number(namespaces, basename) + 1
        user_spec_name = basename + str(new_suffix)

        mod = __import__("Blueprint." + module, {}, {}, [module])
        reload(mod)

        module_class = getattr(mod, mod.CLASS_NAME)
        module_instance = module_class(user_spec_name)
        module_instance.install()

        module_transform = mod.CLASS_NAME + "__" + user_spec_name + ":module_transform"
        cmds.select(module_transform, replace=True)
        cmds.setToolTo("moveSuperContext")

    def lock(self, *args):
        result = cmds.confirmDialog(
            messageAlign="center",
            title="Lock Blueprints",
            message="The action of locking a character will convert the blueprint module to joints. \nThis action cannot be undone. \nModifications to the blueprint cannot be made after this point. \nDo you want to continue?",
            button=["Accept", "Cancel"],
            defaultButton="Accept",
            cancelButton="Cancel",
            dismissString="Cancel",
        )

        if result != "Accept":
            return

        module_info = []  # store  (module, user_specified_name) pairs

        cmds.namespace(setNamespace=":")
        namespaces = cmds.namespaceInfo(listOnlyNamespaces=True)

        module_name_info = utils.find_all_module_names("/Modules/Blueprint")
        valid_modules = module_name_info[0]
        valid_modules_names = module_name_info[1]

        for n in namespaces:
            split_string = n.partition("__")

            if split_string[1] != "":
                module = split_string[0]
                user_specified_name = split_string[2]

                if module in valid_modules_names:
                    index = valid_modules_names.index(module)
                    module_info.append([valid_modules[index], user_specified_name])

        if len(module_info) == 0:
            cmds.confirmDialog(
                messageAlign="center",
                title="Lock Blueprints",
                message="There appears to be no blueprint module \ninstances in the current scene. \nAborting lock.",
                button=["Accept"],
                defaultButton="Accept",
            )
            return
        
        module_instances = []
        for module in module_info:
            mod = __import__("Blueprint."+module[0], {}, {}, [module[0]])
            reload(mod)
            
            module_class = getattr(mod, mod.CLASS_NAME)
            module_inst = module_class(user_specified_name=module[1])
            module_info = module_inst.lock_phase_1()
            
            module_instances.append((module_inst, module_info))

        """def initialize_module_tab(self, tab_height, tab_width):
        # Create a layout for the first tab
        moduleLayout = cmds.columnLayout(adjustableColumn=True)
        cmds.button(label="Module Button")
        cmds.setParent("..")  # Go up to the tabLayout
        
        # Create a layout for the second tab
        settingsLayout = cmds.columnLayout(adjustableColumn=True)
        cmds.button(label="Settings Button")
        cmds.setParent("..")  # Go up to the tabLayout

        # Now, we'll use the "edit" flag on the tabLayout to set the names for our tabs
        cmds.tabLayout(self.UI_elements["tabs"], edit=True, tabLabel=((moduleLayout, "Modules"), (settingsLayout, "Settings")))
        """
