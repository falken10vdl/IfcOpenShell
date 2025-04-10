import bpy
import os

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
    for entry in sorted(os.listdir(path)):
        entry_path = os.path.join(path, entry)
        child_node = bpy.context.scene.file_tree.nodes.add()
        child_node.name = entry
        child_node.full_path = entry_path
        child_node.is_directory = os.path.isdir(entry_path)
        child_node.parent_name = parent_node.name

        if child_node.is_directory:
            _build_tree_recursive(entry_path, child_node)

# ---------------------------------------------
# UI Panel
# ---------------------------------------------
class FileTreePanel(bpy.types.Panel):
    bl_label = "IFC Project File Tree"
    bl_idname = "BIM_PT_ifctree"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    def draw(self, context):

        row = self.layout.row()
        row.label(text="IFC Project File Tree", icon="FILE_FOLDER")
        row.operator("filetree.refresh", text="", icon="IMPORT")

        layout = self.layout
        nodes = context.scene.file_tree.nodes
        if nodes:
            root = nodes[0]
            self.draw_node(layout, root, nodes)

        row = self.layout.row()
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
