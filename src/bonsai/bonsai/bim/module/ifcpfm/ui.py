import bpy
import os
import bonsai.tool as tool


# ---------------------------------------------
# Building the tree
# ---------------------------------------------
def build_file_tree(path):
    print(f"Building file tree for path: {path}")
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
    


def refresh_linked_files(context):
    scene = context.scene



# ---------------------------------------------
# UI Panel
# ---------------------------------------------
class FileTreePanel(bpy.types.Panel):
    bl_label = "IFC Project Files Management"
    bl_idname = "BIM_PT_ifctree"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text=context.scene.BIMProperties.ifc_file, icon="FILE_FOLDER")
        row = layout.row()
        row.label(text="Directory tree:", icon="FILE_FOLDER")
        

        nodes = context.scene.file_tree.nodes
        if nodes:
            root = nodes[0]
            self.draw_node(layout, root, nodes)

        row = layout.row()
        row.operator("filetree.refresh", text="Refresh", icon="FILE_REFRESH")
        
#        row = self.layout.row()
#        row.label(text="Linked Files:", icon="FILE_FOLDER")

#        for link in tool.Project.get_project_props().links:
#            row = self.layout.row()
#            if  os.path.isabs(link.name):
#                row.label(text=link.name, icon="ERROR")
#            else:
#                row.label(text=link.name, icon="LINK_BLEND")

        row = layout.row()
        row.label(text="Linked Files:", icon="FILE_FOLDER")
        if context.scene.show_linked_files:
            row.operator("linkedfiles.review", text="", icon="CANCEL")
            row = layout.row()
            for link in tool.Project.get_project_props().links:
                row = layout.row()
                if os.path.isabs(link.name):
                    row.label(text=link.name, icon="ERROR")
                elif link.name.startswith(".."):
                    row.label(text=link.name, icon="VIEW_PAN")
                else:
                    row.label(text=link.name, icon="LINK_BLEND")
        else:

            row.operator("linkedfiles.review", text="", icon="IMPORT")

        row = layout.row()
        row.operator("filetree.open")

    def draw_node(self, layout, node, all_nodes, level=0):
        icon = 'FILE_FOLDER' if node.is_directory else 'FILE'
        disclosure_icon = 'TRIA_RIGHT' if not node.expanded else 'TRIA_DOWN'

        row = layout.row()
        row.separator(factor=level)
        row.prop(node, "expanded", icon=disclosure_icon, icon_only=True, emboss=False)
        row.prop(node, "enabled", text="")
        row.label(text=node.name, icon=icon)

        if node.is_directory and node.expanded:
            children = [n for n in all_nodes if n.parent_name == node.name]
            for child in children:
                self.draw_node(layout, child, all_nodes, level + 1)
