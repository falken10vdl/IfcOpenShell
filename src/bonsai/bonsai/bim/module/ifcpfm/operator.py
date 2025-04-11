import bpy
import os
from . import ui
import bonsai.tool as tool
from bonsai.bim.module.ifcpfm.data import IfcpfmLinksData

# ---------------------------------------------
# Building the tree
# ---------------------------------------------
def build_file_tree(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"The directory {path} does not exist.")
    if not os.access(path, os.R_OK):
        raise PermissionError(f"Permission denied for accessing the directory {path}.")

    file_tree = bpy.context.scene.file_tree
    file_tree.nodes.clear()

    # Create root node
    root = file_tree.nodes.add()
    root.name = os.path.basename(path) or path
    root.full_path = path
    root.is_directory = True
    root.parent_name = ""

    _build_tree_recursive(path, root)
    return root

def _build_tree_recursive(path, parent_node):
    # Separate directories and files
    directories = []
    files = []

    entries = os.listdir(path)
    for entry in entries:
        entry_path = os.path.join(path, entry)
        if os.path.isdir(entry_path):
            directories.append(entry)
        else:
            files.append(entry)

    # Sort directories and files alphabetically
    directories = sorted(directories, key=lambda x: x.lower())
    files = sorted(files, key=lambda x: x.lower())

    # Process directories first
    for entry in directories:
        entry_path = os.path.join(path, entry)
        child_node = bpy.context.scene.file_tree.nodes.add()
        child_node.name = entry
        child_node.full_path = entry_path
        child_node.is_directory = True
        child_node.parent_name = parent_node.name

        _build_tree_recursive(entry_path, child_node)

    # Process files next
    for entry in files:
        entry_path = os.path.join(path, entry)
        child_node = bpy.context.scene.file_tree.nodes.add()
        child_node.name = entry
        child_node.full_path = entry_path
        child_node.is_directory = False
        child_node.parent_name = parent_node.name
    


class FILETREE_OT_Refresh(bpy.types.Operator):
    bl_idname = "filetree.refresh"
    bl_label = "Refresh File Tree"
    bl_description = "Rebuild the IFC file tree"

    def execute(self, context):
        bpy.context.scene.show_directory_structure= not bpy.context.scene.show_directory_structure
        scene = context.scene
        if hasattr(scene, "BIMProperties") and hasattr(scene.BIMProperties, "ifc_file"):
            ifc_path = scene.BIMProperties.ifc_file
            if ifc_path:
                build_file_tree(os.path.dirname(ifc_path))
                return {'FINISHED'}
        self.report({'WARNING'}, "No IFC file found")
        return {'CANCELLED'}

class FILETREE_OT_Open(bpy.types.Operator):
    bl_idname = "filetree.open"
    bl_label = "Open Project Folder"
    bl_description = "Opens the folder containing the current IFC file"


    def execute(self, context):
        import subprocess
        import platform
        scene = context.scene
        ifc_dir_path = os.path.dirname(scene.BIMProperties.ifc_file)
        if platform.system() == 'Windows':
            subprocess.Popen(f'explorer "{ifc_dir_path}"')
        elif platform.system() == 'Darwin':  # macOS
            subprocess.Popen(["open", ifc_dir_path])
        else:  # Linux
            print (f"Opening {ifc_dir_path} with xdg-open")
            subprocess.Popen(["xdg-open", ifc_dir_path])
        return {'FINISHED'}

class LINKEDFILES_OT_Review(bpy.types.Operator):
    bl_idname = "linkedfiles.review"
    bl_label = "Review Linked Files"
    bl_description = "Review the linked files in the project"

    def execute(self, context):
        IfcpfmLinksData.is_loaded = False
        bpy.context.scene.show_linked_files = not bpy.context.scene.show_linked_files
        return {'FINISHED'}