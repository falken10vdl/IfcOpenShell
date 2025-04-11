import bpy
from bonsai.bim.module.ifcpfm.data import IfcpfmLinksData
import os


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

        if not IfcpfmLinksData.is_loaded:
            IfcpfmLinksData.load()
            
        layout = self.layout
        row = layout.row()
        row.label(text=context.scene.BIMProperties.ifc_file, icon="FILE_FOLDER")
        row.operator("filetree.open", text="", icon="IMPORT")

        row = layout.row()

        row.label(text="Directory tree:", icon="FILE_FOLDER")
        if context.scene.show_directory_structure:
            row.operator("filetree.refresh", text="", icon="CANCEL")
            nodes = context.scene.file_tree.nodes
            if nodes:
                root = nodes[0]
                self.draw_node(layout, root, nodes)
        else:
            row.operator("filetree.refresh", text="", icon="IMPORT")

        row = layout.row()
        row.label(text="Linked Files:", icon="FILE_FOLDER")
        if context.scene.show_linked_files:
            row.operator("linkedfiles.review", text="", icon="CANCEL")
            for linked_file in IfcpfmLinksData.linked_files:
                row = layout.row()
                row.label(text=linked_file["name"], icon=linked_file["icon"])
        else:

            row.operator("linkedfiles.review", text="", icon="IMPORT")


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