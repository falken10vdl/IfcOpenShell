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
from bonsai.bim.helper import draw_attributes
from .data import DocumentLibraryData, ObjectDocumentLibraryData


class BIM_PT_documentlibraries(Panel):
    bl_label = "Document Libraries"
    bl_idname = "BIM_PT_documentlibraries"
    bl_options = {"DEFAULT_CLOSED"}
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_parent_id = "BIM_PT_tab_project_setup"

    @classmethod
    def poll(cls, context):
        return tool.Ifc.get()

    def draw(self, context):
        if not DocumentLibraryData.is_loaded:
            DocumentLibraryData.load()

        self.props = tool.DocumentLibrary.get_library_props()

        row = self.layout.row(align=True)
        split = row.split(factor=0.55)

        left_row = split.row(align=True)
        left_row.label(text="{} Informations".format(DocumentLibraryData.data["total_library_informations"]), icon="ASSET_MANAGER")
        left_row.label(text="{} References".format(DocumentLibraryData.data["total_library_references"]), icon="BOOKMARKS")

        right_row = split.row(align=True)
        right_row.label(text="{} Objects Referenced".format(DocumentLibraryData.data["total_referenced_objects"]), icon="OBJECT_DATA")

        if self.props.is_editing:
            right_row.operator("bim.disable_library_editing_ui", text="", icon="CANCEL")
        else:
            right_row.operator("bim.load_project_document_libraries", text="", icon="IMPORT")

        if not self.props.is_editing:
            return

        row = self.layout.row(align=True)
        row.alignment = "RIGHT"

        if self.props.is_library_editing:
            # When actively editing a library, only show edit/cancel buttons
            row.operator("bim.edit_document_library", text="", icon="CHECKMARK")
            row.operator("bim.disable_editing_document_library", text="", icon="CANCEL")
        else:
            # When not actively editing, show add buttons and other operations
            row.operator("bim.add_library_information", text="", icon="ADD")

            if self.props.libraries and self.props.active_library_index < len(self.props.libraries):
                active_lib = self.props.libraries[self.props.active_library_index]
                if active_lib.is_information and active_lib.ifc_definition_id != -1:
                    row.operator("bim.add_document_library_reference", text="", icon="BOOKMARKS")

            active_library = self.props.active_library
            if active_library:
                ifc_definition_id = active_library.ifc_definition_id
                row.operator("bim.select_library_objects", text="", icon="RESTRICT_SELECT_OFF").library = (
                    ifc_definition_id
                )
                row.operator("bim.assign_library", text="", icon="BRUSH_DATA").library = ifc_definition_id
                row.operator("bim.enable_editing_document_library", text="", icon="GREASEPENCIL").library = ifc_definition_id
                row.operator("bim.remove_document_library", text="", icon="X").library = ifc_definition_id

        self.layout.template_list("BIM_UL_libraries", "", self.props, "libraries", self.props, "active_library_index")

        if self.props.is_library_editing:
            active_library = self.props.active_library
            if active_library.is_information:
                draw_attributes(self.props.library_attributes, self.layout)
            else:
                draw_attributes(self.props.library_attributes, self.layout, filter_attributes=["Name"])


        if self.props.is_editing and self.props.libraries and self.props.active_assigned_library_index < len(self.props.libraries):
            library = self.props.libraries[self.props.active_library_index]
            box = self.layout.box()
            row = box.row(align=True)
            row.label(text="Assigned Objects", icon="OUTLINER_OB_EMPTY")
            box.template_list(
                "BIM_UL_library_objects", 
                "", 
                self.props, 
                "library_objects", 
                self.props, 
                "active_library_object_index"
            )



class BIM_PT_object_libraries(Panel):
    bl_label = "Document Libraries"
    bl_idname = "BIM_PT_object_libraries"
    bl_options = {"DEFAULT_CLOSED"}
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_order = 1
    bl_parent_id = "BIM_PT_tab_misc"

    @classmethod
    def poll(cls, context):
        if not (obj := context.active_object):
            return False
        if not (ifc_id := tool.Blender.get_ifc_definition_id(obj)):
            return False
        if not tool.Ifc.get_object_by_identifier(ifc_id):
            return False
        return True

    def draw(self, context):
        if not ObjectDocumentLibraryData.is_loaded:
            ObjectDocumentLibraryData.load()
        
        obj = context.active_object
        self.oprops = tool.Blender.get_object_bim_props(obj)
        self.props = tool.DocumentLibrary.get_library_props()
        self.file = tool.Ifc.get()
        
        lib_count = len(ObjectDocumentLibraryData.data["libraries"])
        row = self.layout.row(align=True)
        row.label(text="{} Libraries Assigned".format(lib_count), icon="ASSET_MANAGER")
        
        if self.props.is_object_editing:
            row.operator("bim.disable_object_library_editing_ui", text="", icon="CANCEL")
        else:
            row.operator("bim.load_object_libraries", text="", icon="IMPORT")
        
        if not self.props.is_object_editing and lib_count == 0:
            row = self.layout.row()
            row.label(text="No libraries assigned", icon="INFO")
            return
        
        if self.props.is_object_editing:
            self.draw_add_ui()
            if lib_count > 0:
                box = self.layout.box()
                row = box.row(align=True)
                row.label(text="Assigned Libraries", icon="OUTLINER_OB_EMPTY")
                
                box.template_list(
                    "BIM_UL_assigned_libraries",
                    "",
                    self.props,
                    "assigned_libraries",
                    self.props,
                    "active_assigned_library_index"
                )
    
    def draw_add_ui(self):
        if self.props.is_object_editing:
            row = self.layout.row(align=True)
            row.alignment = "RIGHT"

            if self.props.libraries and self.props.active_library_index < len(self.props.libraries):
                library = self.props.libraries[self.props.active_library_index]
                
                assigned_lib_ids = []
                for lib in ObjectDocumentLibraryData.data["libraries"]:
                    assigned_lib_ids.append(lib["id"])
                
                if library.ifc_definition_id not in assigned_lib_ids:
                    row.operator("bim.assign_library", text="", icon="ADD").library = library.ifc_definition_id
                else:
                    row.operator("bim.unassign_library", text="", icon="REMOVE").library = library.ifc_definition_id
            
            self.layout.template_list(
                "BIM_UL_libraries", 
                "", 
                self.props, 
                "libraries", 
                self.props, 
                "active_library_index"
            )


class BIM_UL_libraries(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if item:
            row = layout.row(align=True)
            indent_depth = 0
            
            if item.ifc_definition_id != -1:
                if item.tree_depth > 1:
                    indent_depth = item.tree_depth - 1
            
            for i in range(indent_depth):
                row.label(text="", icon="BLANK1")
            
            if item.ifc_definition_id == -1:
                row.label(text="", icon="OUTLINER_COLLECTION")
                row.label(text=item.name)
                return
            
            if item.is_information and item.has_children:
                op = row.operator(
                    "bim.toggle_library", 
                    icon="TRIA_DOWN" if item.is_expanded else "TRIA_RIGHT", 
                    text="", 
                    emboss=False
                )
                op.library = item.ifc_definition_id
                op.option = "Collapse" if item.is_expanded else "Expand"
            elif item.is_information:
                row.label(text="", icon="BLANK1")
            
            if item.is_information:
                row.label(text="", icon="ASSET_MANAGER")
                text = " - ".join([x for x in [item.name, item.location] if x])
            else:
                row.label(text="", icon="BOOKMARKS")
                text = " - ".join([x for x in [item.description, item.location] if x])
            
            split2 = row.split(factor=0.9)
            if not item.is_information:
                split1 = split2.split(factor=0.1)
                split1.prop(item, "identification", text="", emboss=False)
                split2 = split1.split(factor=0.8)
            
            split2.label(text=text)

            if item.location:
                if item.location.lower().endswith(".ifc"):
                    row.operator("bim.open_ifc_library", icon="HIDE_OFF", text="").uri = item.location
                row.operator("bim.open_uri", icon="URL", text="").uri = item.location


class BIM_UL_library_objects(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if item:
            row = layout.row(align=True)
            row.prop(item, "name", text="", emboss=False, icon="OBJECT_DATA")
            row.operator("bim.select_object", text="", icon="RESTRICT_SELECT_OFF").obj_name = item.name
            
            props = tool.DocumentLibrary.get_library_props()
            if props.libraries and props.active_library_index < len(props.libraries):
                library = props.libraries[props.active_library_index]
                
                op = row.operator("bim.unassign_library", text="", icon="X")
                op.library = library.ifc_definition_id
                op.obj = item.name


class BIM_UL_assigned_libraries(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if item:
            row = layout.row(align=True)
            
            if item.is_information:
                row.label(text="", icon="ASSET_MANAGER")
            else:
                row.label(text="", icon="BOOKMARKS")
                
            split1 = row.split(factor=0.2)
            split1.label(text=item.identification or "")
            
            split2 = split1.split(factor=1.0)
            if item.is_information:
                split2.label(text=item.name or "")
            else:
                split2.label(text=item.description or "")

            if item.location:
                if item.location.lower().endswith(".ifc"):
                    row.operator("bim.open_ifc_document", icon="HIDE_OFF", text="").uri = item.location
                row.operator("bim.open_uri", icon="URL", text="").uri = item.location
            op = row.operator("bim.unassign_document", text="", icon="X")
            op.library = item.ifc_definition_id


def add_object_libraries_context_menu(self, context):
    if not context.active_object:
        return

    if not tool.Blender.get_ifc_definition_id(context.active_object):
        return

    self.layout.menu("BIM_MT_object_libraries_context_menu", icon="ASSET_MANAGER")
    self.layout.separator()


class BIM_MT_object_libraries_context_menu(bpy.types.Menu):
    bl_idname = "BIM_MT_object_libraries_context_menu"
    bl_label = "Document Libraries"

    def draw(self, context):
        layout = self.layout

        if not context.selected_objects:
            layout.label(text="No libraries", icon="INFO")
            return

        if len(context.selected_objects) > 1:
            layout.label(text="Select a single object to see its referenced libraries", icon="INFO")
            return

        obj = context.active_object
        if not obj or not tool.Blender.get_ifc_definition_id(obj):
            layout.label(text="No libraries", icon="INFO")
            return

        if not ObjectDocumentLibraryData.is_loaded:
            ObjectDocumentLibraryData.load()

        if not ObjectDocumentLibraryData.data.get("libraries", []):
            layout.label(text="No Libraries", icon="ASSET_MANAGER")
        else:
            for library in ObjectDocumentLibraryData.data["libraries"]:
                row = layout.row(align=True)

                with_ifc_icon = library.get("location", "") and library["location"].lower().endswith(".ifc")
                with_url_icon = bool(library.get("location", ""))
                
                if with_ifc_icon:
                    row.operator("bim.open_ifc_library", icon="HIDE_OFF", text="").uri = library["location"]
                else:
                    row.label(text="", icon="BLANK1")
                
                if with_url_icon:
                    row.operator("bim.open_uri", icon="URL", text="").uri = library["location"]
                else:
                    row.label(text="", icon="BLANK1")
                
                lib_entity = None
                if "id" in library:
                    lib_entity = tool.Ifc.get().by_id(library["id"])

                if lib_entity and lib_entity.is_a("IfcLibraryReference"):
                    display_text = library.get("description") or ""
                else:
                    display_text = library.get("name") or ""
                
                # Safely access identification
                identification = library.get("identification", "")
                if identification:
                    row.label(text=f"{identification}: {display_text}")
                else:
                    row.label(text=display_text)
