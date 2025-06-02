# Bonsai - OpenBIM Blender Add-on
# Copyright (C) 2020, 2021, 2022 Dion Moult <dion@thinkmoult.com>
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
import json
import ifcopenshell.api
import ifcopenshell.util.attribute
import ifcopenshell.util.element
import bonsai.bim.handler
import bonsai.tool as tool
import bonsai.core.documentLibrary as core
from .data import ObjectDocumentLibraryData, DocumentLibraryData


class LoadProjectDocumentLibraries(bpy.types.Operator):
    bl_idname = "bim.load_project_document_libraries"
    bl_label = "Load Project Document Libraries"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        core.load_project_document_libraries(tool.DocumentLibrary)
        bonsai.bim.handler.refresh_ui_data()  # Update breadcrumbs data.
        return {"FINISHED"}


class LoadDocumentLibrary(bpy.types.Operator):
    bl_idname = "bim.load_document_library"
    bl_label = "Load Document Library"
    bl_options = {"REGISTER", "UNDO"}
    document_library: bpy.props.IntProperty()

    def execute(self, context):
        core.load_document_library(tool.DocumentLibrary, doclib_entity=tool.Ifc.get().by_id(self.document_library))
        bonsai.bim.handler.refresh_ui_data()  # Update breadcrumbs data.
        return {"FINISHED"}


class LoadParentDocumentLibrary(bpy.types.Operator):
    bl_idname = "bim.load_parent_document_library"
    bl_label = "Load Parent Document Library"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        core.load_parent_document_library(tool.DocumentLibrary)
        bonsai.bim.handler.refresh_ui_data()  # Update breadcrumbs data.
        return {"FINISHED"}


class DisableDocumentLibraryEditingUI(bpy.types.Operator):
    bl_idname = "bim.disable_document_library_editing_ui"
    bl_label = "Disable Document Library Editing UI"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        core.disable_document_library_editing_ui(tool.DocumentLibrary)
        return {"FINISHED"}


class EnableEditingDocumentLibrary(bpy.types.Operator):
    bl_idname = "bim.enable_editing_document_library"
    bl_label = "Enable Editing Document Library"
    bl_options = {"REGISTER", "UNDO"}
    document_library: bpy.props.IntProperty()

    def execute(self, context):
        core.enable_editing_document_library(tool.DocumentLibrary, doclib_entity=tool.Ifc.get().by_id(self.document_library))
        return {"FINISHED"}


class DisableEditingDocumentLibrary(bpy.types.Operator):
    bl_idname = "bim.disable_editing_document_library"
    bl_label = "Disable Editing Document Library"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        core.disable_editing_document_library(tool.DocumentLibrary)
        return {"FINISHED"}


class AddDocumentLibraryInformation(bpy.types.Operator, tool.Ifc.Operator):
    bl_idname = "bim.add_document_library_information"
    bl_label = "Add Library Information"
    bl_options = {"REGISTER", "UNDO"}

    def _execute(self, context):
        core.add_library_information(tool.Ifc, tool.DocumentLibrary)


class AddDocumentLibraryReference(bpy.types.Operator, tool.Ifc.Operator):
    bl_idname = "bim.add_document_library_reference"
    bl_label = "Add Library Reference"
    bl_options = {"REGISTER", "UNDO"}

    def _execute(self, context):
        core.add_library_reference(tool.Ifc, tool.DocumentLibrary)


class EditDocumentLibrary(bpy.types.Operator, tool.Ifc.Operator):
    bl_idname = "bim.edit_document_library"
    bl_label = "Edit Document Library"
    bl_options = {"REGISTER", "UNDO"}

    def _execute(self, context):
        props = tool.DocumentLibrary.get_document_library_props()
        core.edit_document_library(tool.Ifc, tool.DocumentLibrary, doclib_entity=tool.Ifc.get().by_id(props.active_document_library_id))


class RemoveDocumentLibrary(bpy.types.Operator, tool.Ifc.Operator):
    bl_idname = "bim.remove_document_library"
    bl_label = "Remove Document Library"
    bl_options = {"REGISTER", "UNDO"}
    document_library: bpy.props.IntProperty()

    def _execute(self, context):
        core.remove_document_library(tool.Ifc, tool.DocumentLibrary, doclib_entity=tool.Ifc.get().by_id(self.document_library))


class AssignDocumentLibrary(bpy.types.Operator, tool.Ifc.Operator):
    bl_idname = "bim.assign_document_library"
    bl_label = "Assign Document Library"
    bl_description = "Assign active document library to the selected objects."
    bl_options = {"REGISTER", "UNDO"}
    obj: bpy.props.StringProperty()
    document_library: bpy.props.IntProperty()

    def _execute(self, context):
        document_library = tool.Ifc.get().by_id(self.document_library)
        objs = [bpy.data.objects[self.obj]] if self.obj else tool.Blender.get_selected_objects()
        for obj in objs:
            element = tool.Ifc.get_entity(obj)
            if element:
                core.assign_document_library(tool.Ifc, product=element, document_library=document_library)


class UnassignDocumentLibrary(bpy.types.Operator, tool.Ifc.Operator):
    bl_idname = "bim.unassign_document_library"
    bl_label = "Unassign Document Library"
    bl_options = {"REGISTER", "UNDO"}
    obj: bpy.props.StringProperty()
    document_library: bpy.props.IntProperty()

    def _execute(self, context):
        document_library = tool.Ifc.get().by_id(self.document_library)
        objs = [bpy.data.objects.get(self.obj)] if self.obj else tool.Blender.get_selected_objects()
        for obj in objs:
            element = tool.Ifc.get_entity(obj)
            if element:
                core.unassign_document_library(tool.Ifc, product=element, document_library=document_library)


class SelectDocumentLibraryObjects(bpy.types.Operator):
    bl_idname = "bim.select_document_library_objects"
    bl_label = "Select Document Library Objects"
    bl_options = {"REGISTER", "UNDO"}
    document_library: bpy.props.IntProperty(name="Document Library ID", default=0)

    def execute(self, context):
        if not self.document_library or not (relating_library := tool.Ifc.get_entity_by_id(self.document_library)):
            self.report({"INFO"}, f"No document library found by id '{self.document_library}'.")
            return {"FINISHED"}

        i = 0
        for element in ifcopenshell.util.element.get_referenced_elements(relating_library):
            obj = tool.Ifc.get_object(element)
            if not obj or obj not in context.selectable_objects:
                continue
            obj.select_set(True)
            i += 1
        self.report({"INFO"}, f"{i} objects selected.")
        return {"FINISHED"}


class AssignSelectedObjectsToDocumentLibrary(bpy.types.Operator, tool.Ifc.Operator):
    bl_idname = "bim.assign_selected_objects_to_document_library"
    bl_label = "Assign Selected Objects To Document Library"
    bl_options = {"REGISTER", "UNDO"}
    document_library: bpy.props.IntProperty(name="Document Library ID", default=0)

    def _execute(self, context):
        if not self.document_library:
            self.report({"ERROR"}, "No document library selected")
            return

        document_library = tool.Ifc.get().by_id(self.document_library)
        if not document_library:
            self.report({"ERROR"}, "Invalid document library")
            return

        selected_objects = [obj for obj in context.selected_objects if tool.Blender.get_ifc_definition_id(obj)]
        if not selected_objects:
            self.report({"ERROR"}, "No IFC objects selected")
            return

        for obj in selected_objects:
            ifc_entity = tool.Ifc.get_entity(obj)
            if ifc_entity:
                tool.Ifc.run("library.assign_library", products=[ifc_entity], library=document_library)

        # Refresh document library data after assignment
        ObjectDocumentLibraryData.load()
        DocumentLibraryData.load()
        props = tool.DocumentLibrary.get_document_library_props()
        tool.DocumentLibrary.load_referenceable_objects(document_library)

        self.report({"INFO"}, f"Assigned {len(selected_objects)} objects to document library")


class RemoveObjectFromDocumentLibraryReference(bpy.types.Operator, tool.Ifc.Operator):
    bl_idname = "bim.remove_object_from_document_library_reference"
    bl_label = "Remove Object From Document Library Reference"
    bl_options = {"REGISTER", "UNDO"}
    document_library: bpy.props.IntProperty(name="Document Library ID", default=0)
    object: bpy.props.IntProperty(name="Object ID", default=0)

    def _execute(self, context):
        if not self.document_library or not self.object:
            self.report({"ERROR"}, "Invalid document library or object")
            return

        document_library = tool.Ifc.get().by_id(self.document_library)
        product = tool.Ifc.get().by_id(self.object)

        if document_library and product:
            tool.Ifc.run("library.unassign_library", products=[product], library=document_library)

            # Refresh document library data after removal
            ObjectDocumentLibraryData.load()
            DocumentLibraryData.load()
            props = tool.DocumentLibrary.get_document_library_props()
            tool.DocumentLibrary.load_referenceable_objects(document_library)

            self.report({"INFO"}, f"Removed object from document library")


class OpenIFCDocumentLibrary(bpy.types.Operator):
    bl_idname = "bim.open_ifc_document_library"
    bl_label = "Open IFC Document Library"
    bl_description = "Open the IFC document library in a new Blender instance and load the project"
    bl_options = {"REGISTER", "UNDO"}

    uri: bpy.props.StringProperty(name="URI")

    def execute(self, context):
        import subprocess
        import os

        if not self.uri:
            self.report({"ERROR"}, "No URI provided")
            return {"CANCELLED"}

        file_path = self.uri
        if file_path.startswith("file://"):
            file_path = file_path[7:]
        elif file_path.startswith("file:"):
            file_path = file_path[5:]

        if not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)

        if not os.path.exists(file_path):
            self.report({"ERROR"}, f"IFC file not found: {file_path}")
            return {"CANCELLED"}

        try:
            subprocess.Popen(
                [
                    "blender",
                    "--python-expr",
                    f"import bpy; bpy.ops.bim.load_project(filepath='{file_path}', should_start_fresh_session=True)",
                ]
            )
            self.report({"INFO"}, f"Opening IFC file: {file_path} in a new Blender instance.")
        except Exception as e:
            self.report({"ERROR"}, f"Failed to open IFC file: {str(e)}")

        return {"FINISHED"}
