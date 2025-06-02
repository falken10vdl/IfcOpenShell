# Bonsai - OpenBIM Blender Add-on
# Copyright (C) 2020, 2021 Dion Moult <dion@thinkmoult.com>
#
# This file is part of Bonsai.
#
# Bonsai is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Bonsai is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Bonsai.  If not, see <http://www.gnu.org/licenses/>.

import bpy
import bonsai.tool as tool
from bpy.types import Panel, UIList
from bonsai.bim.helper import draw_attributes, draw_document_library_referenced_objects
from bonsai.bim.module.documentLibrary.data import DocumentLibraryData, ObjectDocumentLibraryData


class BIM_PT_document_libraries(Panel):
    """Panel shown in the Project Setup tab for Document Libraries."""
    bl_label = "Document Libraries"
    bl_idname = "BIM_PT_document_libraries"
    bl_options = {"DEFAULT_CLOSED"}
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_parent_id = "BIM_PT_tab_project_setup"
    bl_order = 2

    @classmethod
    def poll(cls, context):
        return tool.Ifc.get()

    def draw(self, context):
        if not DocumentLibraryData.is_loaded:
            DocumentLibraryData.load()

        self.props = tool.DocumentLibrary.get_document_library_props()

        row = self.layout.row(align=True)
        row.label(
            text="{} Root Document Libraries Found".format(DocumentLibraryData.data.get("total_information", 0)),
            icon="FILE",
        )

        if self.props.is_editing:
            row.operator("bim.disable_document_library_editing_ui", text="", icon="CANCEL")
        else:
            row.operator("bim.load_project_document_libraries", text="", icon="IMPORT")

        # If not editing, don't show deeper UI
        if not self.props.is_editing:
            return

        # Breadcrumb navigation
        row = self.layout.row(align=True)
        if self.props.document_library_breadcrumbs:
            row.operator("bim.load_parent_document_library", text="", icon="FRAME_PREV")
            row.label(text=DocumentLibraryData.data.get("parent_document_library", ""))
        else:
            row.alignment = "RIGHT"

        row.operator("bim.add_document_library_information", text="", icon="ADD")
        if self.props.document_library_breadcrumbs:
            row.operator("bim.add_document_library_reference", text="", icon="FILE_HIDDEN")

        active_doclib = self.props.active_document_library
        if self.props.active_document_library_id:
            row.operator("bim.edit_document_library", text="", icon="CHECKMARK")
            row.operator("bim.disable_editing_document_library", text="", icon="CANCEL")
        elif active_doclib:
            ifc_definition_id = active_doclib.ifc_definition_id
            row.operator("bim.select_document_library_objects", text="", icon="RESTRICT_SELECT_OFF").document_library = ifc_definition_id
            row.operator("bim.assign_document_library", text="", icon="BRUSH_DATA").document_library = ifc_definition_id
            row.operator("bim.enable_editing_document_library", text="", icon="GREASEPENCIL").document_library = ifc_definition_id
            row.operator("bim.remove_document_library", text="", icon="X").document_library = ifc_definition_id

        # List of libraries
        self.layout.template_list(
            "BIM_UL_document_libraries", "", 
            self.props, "document_libraries", 
            self.props, "active_document_library_index"
        )

        # Show attributes and referenced objects if there is an active library
        if self.props.active_document_library_id:
            draw_attributes(self.props.document_library_attributes, self.layout)
            draw_document_library_referenced_objects(self.layout, self.props)


class BIM_PT_object_document_libraries(Panel):
    """Panel shown in the Misc tab for Document Libraries related to the active object."""
    bl_label = "Document Libraries"
    bl_idname = "BIM_PT_object_document_libraries"
    bl_options = {"DEFAULT_CLOSED"}
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_order = 2
    bl_parent_id = "BIM_PT_tab_misc"

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if not obj:
            return False
        ifc_id = tool.Blender.get_ifc_definition_id(obj)
        if not ifc_id or not tool.Ifc.get_object_by_identifier(ifc_id):
            return False
        return True

    def draw(self, context):
        if not ObjectDocumentLibraryData.is_loaded:
            ObjectDocumentLibraryData.load()

        obj = context.active_object
        self.oprops = tool.Blender.get_object_bim_props(obj)
        self.props = tool.DocumentLibrary.get_document_library_props()

        self.draw_add_ui()

        # If no libraries, show a label
        if not ObjectDocumentLibraryData.data.get("document_libraries"):
            row = self.layout.row(align=True)
            row.label(text="No Document Libraries", icon="FILE")

        # Otherwise, show each library
        for doclib in ObjectDocumentLibraryData.data["document_libraries"]:
            row = self.layout.row(align=True)
            row.label(text=doclib["identification"] or "", icon="FILE")
            
            # Check if this is a library reference and show description if available
            if "is_reference" in doclib and doclib["is_reference"]:
                # For references, prefer description over name
                display_text = doclib.get("description") or doclib["name"] or "Unnamed"
            else:
                # For library information, continue using name
                display_text = doclib["name"] or "Unnamed"
                
            row.label(text=display_text)
            
            if doclib["location"]:
                if doclib["location"].lower().endswith(".ifc"):
                    row.operator("bim.open_ifc_document_library", icon="HIDE_OFF", text="").uri = doclib["location"]
                row.operator("bim.open_uri", icon="URL", text="").uri = doclib["location"]
            row.operator("bim.unassign_document_library", text="", icon="X").document_library = doclib["id"]

    def draw_add_ui(self):
        if not self.props.is_editing:
            row = self.layout.row(align=True)
            row.operator("bim.load_project_document_libraries", text="Assign Document Library References", icon="ADD")
            return

        row = self.layout.row(align=True)
        if self.props.document_library_breadcrumbs:
            # Go up one breadcrumb if possible
            row.operator("bim.load_parent_document_library", text="", icon="FRAME_PREV")
            row.label(text=DocumentLibraryData.data.get("parent_document_library", ""))
        else:
            row.alignment = "RIGHT"

        if self.props.document_libraries and self.props.active_document_library_index < len(self.props.document_libraries):
            doclib_item = self.props.document_libraries[self.props.active_document_library_index]
            if not doclib_item.is_information:
                row.operator("bim.assign_document_library", text="", icon="ADD").document_library = doclib_item.ifc_definition_id

        row.operator("bim.disable_document_library_editing_ui", text="", icon="CANCEL")

        self.layout.template_list(
            "BIM_UL_document_libraries",
            "",
            self.props,
            "document_libraries",
            self.props,
            "active_document_library_index",
        )


class BIM_UL_document_libraries(UIList):
    """List UI for Document Libraries."""

    def get_referenced_objects(self, library_id):
        """Get names of objects referenced by this document"""
        if not DocumentLibraryData.is_loaded:
            DocumentLibraryData.load()
        return DocumentLibraryData.data["document_library_references"].get(library_id, [])

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if item:
            row = layout.row(align=True)

            if item.is_information:
                op = row.operator("bim.load_document_library", text="", emboss=False, icon="DISCLOSURE_TRI_RIGHT")
                op.document_library = item.ifc_definition_id
                row.label(text="", icon="FILE")
            else:
                row.label(text="", icon="BLANK1")
                row.label(text="", icon="FILE_HIDDEN")

            split1 = row.split(factor=0.1)
            split1.prop(item, "identification", text="", emboss=False)
            split2 = split1.split(factor=0.7)
            split2.prop(item, "name", text="", emboss=False)

            split3 = split2.split()
            referenced_objects = self.get_referenced_objects(item.ifc_definition_id)
            if referenced_objects:
                object_names = ", ".join(referenced_objects[:3])
                if len(referenced_objects) > 3:
                    object_names += f" +{len(referenced_objects) - 3}"
                split3.label(text=object_names)
            else:
                split3.label(text="")


class BIM_UL_document_library_referenced_objects(UIList):
    """List UI for objects assigned to a particular Document Library."""
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type == "DEFAULT":
            row = layout.row(align=True)
            row.label(text=item.name)
            op = row.operator("bim.remove_object_from_document_library_reference", text="", icon="X")
            op.document_library = active_data.active_document_library_id
            op.object = item.ifc_definition_id


def add_object_document_libraries_context_menu(self, context):
    """Optional context menu for Document Libraries in object view."""
    obj = context.active_object
    if not obj or not tool.Blender.get_ifc_definition_id(obj):
        return

    self.layout.menu("BIM_MT_object_document_libraries_context_menu", icon="FILE")
    self.layout.separator()



class BIM_MT_object_document_libraries_context_menu(bpy.types.Menu):
    """Shows existing Document Libraries for an object in a context menu."""
    bl_idname = "BIM_MT_object_document_libraries_context_menu"
    bl_label = "Document Libraries"

    def draw(self, context):
        layout = self.layout
        # Make the menu wider by using a wide empty label at the top
        #layout.label(text="                                                                      ")
        
        if not context.selected_objects:
            layout.label(text="No document libraries", icon="INFO")
            return

        if len(context.selected_objects) > 1:
            layout.label(text="Select a single object to see its referenced libraries", icon="INFO")
            return

        obj = context.active_object
        if not obj or not tool.Blender.get_ifc_definition_id(obj):
            layout.label(text="No document libraries", icon="INFO")
            return

        if not ObjectDocumentLibraryData.is_loaded:
            ObjectDocumentLibraryData.load()

        if not ObjectDocumentLibraryData.data.get("document_libraries"):
            layout.label(text="No Document Libraries", icon="FILE")
        else:
            for doclib in ObjectDocumentLibraryData.data["document_libraries"]:
                row = layout.row(align=True)
                row.alignment = 'LEFT'
                
                with_ifc_icon = doclib["location"] and doclib["location"].lower().endswith(".ifc")
                if with_ifc_icon:
                    row.operator("bim.open_ifc_document_library", icon="HIDE_OFF", text="").uri = doclib["location"]
                else:
                    row.label(text="", icon="BLANK1")
                
                with_url_icon = bool(doclib["location"])
                if with_url_icon:
                    row.operator("bim.open_uri", icon="URL", text="").uri = doclib["location"]
                else:
                    row.label(text="", icon="BLANK1")
                
                row.label(text=f"{doclib['identification'] or ''}: {doclib['name'] or 'Unnamed'}")
