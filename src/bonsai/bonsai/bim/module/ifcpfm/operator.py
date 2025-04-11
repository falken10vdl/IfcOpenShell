import bpy
import os
from . import ui
import bonsai.tool as tool

class FILETREE_OT_Refresh(bpy.types.Operator):
    bl_idname = "filetree.refresh"
    bl_label = "Refresh File Tree"
    bl_description = "Rebuild the IFC file tree"

    def execute(self, context):
        scene = context.scene
        if hasattr(scene, "BIMProperties") and hasattr(scene.BIMProperties, "ifc_file"):
            ifc_path = scene.BIMProperties.ifc_file
            if ifc_path:
                ui.build_file_tree(os.path.dirname(ifc_path))
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
        context.scene.show_linked_files = not context.scene.show_linked_files
        return {'FINISHED'}