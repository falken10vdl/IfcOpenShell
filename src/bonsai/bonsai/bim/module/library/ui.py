# Bonsai - OpenBIM Blender Add-on
# Copyright (C) 2021 Dion Moult <dion@thinkmoult.com>
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

from __future__ import annotations
import bpy
import bonsai.bim.helper
import bonsai.tool as tool
from bpy.types import Panel, UIList
from bonsai.bim.module.library.data import LibrariesData, LibraryReferencesData
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bonsai.bim.module.library.prop import BIMLibraryProperties, LibraryReference


class BIM_PT_libraries(Panel):
    bl_label = "Libraries"
    bl_idname = "BIM_PT_libraries"
    bl_options = {"DEFAULT_CLOSED"}
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_parent_id = "BIM_PT_tab_project_setup"

    @classmethod
    def poll(cls, context):
        return tool.Ifc.get()

    def draw(self, context):
        if not LibrariesData.is_loaded:
            LibrariesData.load()
        self.props = tool.Library.get_library_props()

        row = self.layout.row(align=True)
        row.label(text="{} Libraries Found".format(len(LibrariesData.data["libraries"])), icon="ASSET_MANAGER")
        if self.props.editing_mode == "NONE":
            row.operator("bim.load_project_libraries", text="", icon="IMPORT")
        else:
            row.operator("bim.disable_library_editing_ui", text="", icon="CANCEL")

        if self.props.editing_mode == "LIBRARY":
            self.draw_editable_library_ui()
        elif self.props.editing_mode == "REFERENCE":
            self.draw_editable_reference_ui()
        elif self.props.editing_mode == "REFERENCES":
            self.draw_editable_references_ui()
        elif self.props.editing_mode == "READONLY":
            self.draw_readonly_library_ui()

        if not self.props.editing_mode:
            return


    def draw_editable_library_ui(self):
        row = self.layout.row(align=True)
        row.operator("bim.edit_library", icon="CHECKMARK")
        row.operator("bim.disable_editing_library", text="", icon="CANCEL")
        bonsai.bim.helper.draw_attributes(self.props.library_attributes, self.layout)

    def draw_editable_references_ui(self):
        row = self.layout.row(align=True)
        row.operator("bim.enable_editing_library", icon="GREASEPENCIL")
        row.operator("bim.disable_editing_library_references", text="", icon="CANCEL")

        for attribute in LibrariesData.data["library_attributes"]:
            row = self.layout.row(align=True)
            row.label(text=attribute["name"])
            row.label(text=attribute["value"])

        row = self.layout.row(align=True)
        row.operator("bim.add_library_reference", icon="ADD")

        self.layout.template_list(
            "BIM_UL_library_references", "", self.props, "references", self.props, "active_reference_index"
        )

        for attribute in LibrariesData.data["reference_attributes"]:
            row = self.layout.row(align=True)
            row.label(text=attribute["name"])
            row.label(text=attribute["value"])

    def draw_editable_reference_ui(self):
        row = self.layout.row(align=True)
        row.operator("bim.edit_library_reference", icon="CHECKMARK")
        row.operator("bim.disable_editing_library_reference", text="", icon="CANCEL")
        bonsai.bim.helper.draw_attributes(self.props.reference_attributes, self.layout)

    def draw_readonly_library_ui(self):
        row = self.layout.row()
        row.operator("bim.add_library", icon="ADD")
        for library in LibrariesData.data["libraries"]:
            row = self.layout.row(align=True)
            row.label(text=library["name"], icon="ASSET_MANAGER")
            row.operator("bim.enable_editing_library_references", text="", icon="OUTLINER").library = library["id"]
            row.operator("bim.remove_library", text="", icon="X").library = library["id"]




class BIM_PT_object_libraries(Panel):
    bl_label = "Libraries"
    bl_idname = "BIM_PT_object_libraries"
    bl_options = {"DEFAULT_CLOSED"}
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
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
        if not LibraryReferencesData.is_loaded:
            LibraryReferencesData.load()

        obj = context.active_object
        self.oprops = tool.Blender.get_object_bim_props(obj)
        self.props = tool.Library.get_library_props()
        self.file = tool.Ifc.get()

        self.draw_add_ui()

        if not LibraryReferencesData.data["references"]:
            row = self.layout.row(align=True)
            row.label(text="No Libraries", icon="ASSET_MANAGER")

        for reference in LibraryReferencesData.data["references"]:
            row = self.layout.row(align=True)
            row.label(text=reference["identification"], icon="ASSET_MANAGER")
            row.label(text=reference.get("name", "") or "Unnamed")
            
            if reference.get("location"):
                if reference["location"].lower().endswith(".ifc"):
                    row.operator("bim.open_ifc_document", icon="HIDE_OFF", text="").uri = reference["location"]
                row.operator("bim.open_uri", icon="URL", text="").uri = reference["location"]
                
            row.operator("bim.unassign_library_reference", text="", icon="X").reference = reference["id"]
    
    def draw_add_ui(self):
        if not self.props.editing_mode == "REFERENCES":
            row = self.layout.row(align=True)
            row.operator("bim.load_library", text="Assign Library References", icon="ADD")
            return

        row = self.layout.row(align=True)
        row.alignment = "RIGHT"

        if self.props.references and self.props.active_reference_index < len(self.props.references):
            reference = self.props.references[self.props.active_reference_index]
            row.operator("bim.assign_library_reference", text="", icon="ADD").reference = reference.ifc_definition_id
        row.operator("bim.disable_editing_library_references", text="", icon="CANCEL")

        self.layout.template_list(
            "BIM_UL_object_library_references", 
            "", 
            self.props, 
            "references", 
            self.props, 
            "active_reference_index"
        )


class BIM_UL_library_references(UIList):
    def draw_item(
        self, context, layout: bpy.types.UILayout, data, item: LibraryReference, icon, active_data, active_propname
    ):
        if item:
            row = layout.row(align=True)
            row.prop(item, "name", text="", emboss=False)
            op = row.operator("bim.enable_editing_library_reference", text="", icon="GREASEPENCIL")
            op.reference = item.ifc_definition_id
            op = row.operator("bim.remove_library_reference", text="", icon="X")
            op.reference = item.ifc_definition_id


class BIM_UL_object_library_references(UIList):
    def draw_item(
        self, context, layout: bpy.types.UILayout, data, item: LibraryReference, icon, active_data, active_propname
    ):
        if item:
            row = layout.row(align=True)
            row.prop(item, "name", text="", emboss=False)
            op = row.operator("bim.assign_library_reference", text="", icon="ADD")
            op.reference = item.ifc_definition_id
