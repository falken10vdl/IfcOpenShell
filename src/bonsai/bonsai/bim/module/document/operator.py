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
import bonsai.core.document as core
from .data import ObjectDocumentData, DocumentData


class LoadProjectDocuments(bpy.types.Operator):
    bl_idname = "bim.load_project_documents"
    bl_label = "Load Project Documents"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        core.load_project_documents(tool.Document)
        
        # Set active document after loading documents to trigger referenced objects update
        props = tool.Document.get_document_props()
        if props.documents and len(props.documents) > 0:
            props.active_document_id = 0
            
        bonsai.bim.handler.refresh_ui_data()  # Update breadcrumbs data
        return {"FINISHED"}


class LoadDocument(bpy.types.Operator):
    bl_idname = "bim.load_document"
    bl_label = "Load Document"
    bl_options = {"REGISTER", "UNDO"}
    document: bpy.props.IntProperty()

    def execute(self, context):
        document_entity = tool.Ifc.get().by_id(self.document)
        core.load_document(tool.Document, document=document_entity)
        props = tool.Document.get_document_props()
        props.active_document_id = 0
        
        props.active_document_id = self.document
        tool.Document.load_referenceable_objects(document_entity)
        bonsai.bim.handler.refresh_ui_data()  # Update breadcrumbs data
        return {"FINISHED"}

class LoadParentDocument(bpy.types.Operator):
    bl_idname = "bim.load_parent_document"
    bl_label = "Load Parent Document"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        core.load_parent_document(tool.Document)
        bonsai.bim.handler.refresh_ui_data()  # Update breadcrumbs data.
        return {"FINISHED"}


class DisableDocumentEditingUI(bpy.types.Operator):
    bl_idname = "bim.disable_document_editing_ui"
    bl_label = "Disable Document Editing UI"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        core.disable_document_editing_ui(tool.Document)
        return {"FINISHED"}


class EnableEditingDocument(bpy.types.Operator):
    bl_idname = "bim.enable_editing_document"
    bl_label = "Enable Editing Document"
    bl_options = {"REGISTER", "UNDO"}
    document: bpy.props.IntProperty()

    def execute(self, context):
        core.enable_editing_document(tool.Document, document=tool.Ifc.get().by_id(self.document))
        return {"FINISHED"}


class DisableEditingDocument(bpy.types.Operator):
    bl_idname = "bim.disable_editing_document"
    bl_label = "Disable Editing Document"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        core.disable_editing_document(tool.Document)
        return {"FINISHED"}


class AddInformation(bpy.types.Operator, tool.Ifc.Operator):
    bl_idname = "bim.add_information"
    bl_label = "Add Information"
    bl_options = {"REGISTER", "UNDO"}

    def _execute(self, context):
        core.add_information(tool.Ifc, tool.Document)


class AddDocumentReference(bpy.types.Operator, tool.Ifc.Operator):
    bl_idname = "bim.add_document_reference"
    bl_label = "Add Document Reference"
    bl_options = {"REGISTER", "UNDO"}

    def _execute(self, context):
        core.add_reference(tool.Ifc, tool.Document)


class EditDocument(bpy.types.Operator, tool.Ifc.Operator):
    bl_idname = "bim.edit_document"
    bl_label = "Edit Information"
    bl_options = {"REGISTER", "UNDO"}

    def _execute(self, context):
        props = tool.Document.get_document_props()
        core.edit_document(tool.Ifc, tool.Document, document=tool.Ifc.get().by_id(props.active_document_id))


class RemoveDocument(bpy.types.Operator, tool.Ifc.Operator):
    bl_idname = "bim.remove_document"
    bl_label = "Remove Document"
    bl_options = {"REGISTER", "UNDO"}
    document: bpy.props.IntProperty()

    def _execute(self, context):
        core.remove_document(tool.Ifc, tool.Document, document=tool.Ifc.get().by_id(self.document))


class AssignDocument(bpy.types.Operator, tool.Ifc.Operator):
    bl_idname = "bim.assign_document"
    bl_label = "Assign Document"
    bl_description = "Assign active document to the selected objects."
    bl_options = {"REGISTER", "UNDO"}
    obj: bpy.props.StringProperty()
    document: bpy.props.IntProperty()

    def _execute(self, context):
        document = tool.Ifc.get().by_id(self.document)
        objs = [bpy.data.objects[self.obj]] if self.obj else tool.Blender.get_selected_objects()
        for obj in objs:
            element = tool.Ifc.get_entity(obj)
            if element:
                core.assign_document(tool.Ifc, product=element, document=document)


class UnassignDocument(bpy.types.Operator, tool.Ifc.Operator):
    bl_idname = "bim.unassign_document"
    bl_label = "Unassign Document"
    bl_options = {"REGISTER", "UNDO"}
    obj: bpy.props.StringProperty()
    document: bpy.props.IntProperty()

    def _execute(self, context):
        document = tool.Ifc.get().by_id(self.document)
        objs = [bpy.data.objects.get(self.obj)] if self.obj else tool.Blender.get_selected_objects()
        for obj in objs:
            element = tool.Ifc.get_entity(obj)
            if element:
                core.unassign_document(tool.Ifc, product=element, document=document)


class SelectDocumentObjects(bpy.types.Operator):
    bl_idname = "bim.select_document_objects"
    bl_label = "Select Document Objects"
    bl_options = {"REGISTER", "UNDO"}
    document: bpy.props.IntProperty(name="Document ID", default=0)

    def execute(self, context):
        if not self.document or not (relating_document := tool.Ifc.get_entity_by_id(self.document)):
            self.report({"INFO"}, f"No document found by id '{self.document}'.")
            return {"FINISHED"}

        i = 0
        for element in ifcopenshell.util.element.get_referenced_elements(relating_document):
            obj = tool.Ifc.get_object(element)
            if not obj or obj not in context.selectable_objects:
                continue
            obj.select_set(True)
            i += 1
        self.report({"INFO"}, f"{i} objects selected.")
        return {"FINISHED"}


class AssignSelectedObjectsToDocument(bpy.types.Operator, tool.Ifc.Operator):
    bl_idname = "bim.assign_selected_objects_to_document"
    bl_label = "Assign Selected Objects To Document"
    bl_options = {"REGISTER", "UNDO"}
    document: bpy.props.IntProperty(name="Document ID", default=0)

    def _execute(self, context):
        if not self.document:
            self.report({"ERROR"}, "No document selected")
            return

        document = tool.Ifc.get().by_id(self.document)
        if not document:
            self.report({"ERROR"}, "Invalid document")
            return

        selected_objects = [obj for obj in context.selected_objects if tool.Blender.get_ifc_definition_id(obj)]
        if not selected_objects:
            self.report({"ERROR"}, "No IFC objects selected")
            return

        # Sort selected objects by name before assigning them to maintain order
        selected_objects.sort(key=lambda obj: obj.name.lower())

        for obj in selected_objects:
            ifc_entity = tool.Ifc.get_entity(obj)
            if ifc_entity:
                tool.Ifc.run("document.assign_document", products=[ifc_entity], document=document)

        # Refresh document data after assignment
        ObjectDocumentData.load()
        DocumentData.load()
        props = tool.Document.get_document_props()
        tool.Document.load_referenceable_objects(document)

        self.report({"INFO"}, f"Assigned {len(selected_objects)} objects to document")


class RemoveObjectFromDocumentReference(bpy.types.Operator, tool.Ifc.Operator):
    bl_idname = "bim.remove_object_from_document_reference"
    bl_label = "Remove Object From Document Reference"
    bl_options = {"REGISTER", "UNDO"}
    document: bpy.props.IntProperty(name="Document ID", default=0)
    object: bpy.props.IntProperty(name="Object ID", default=0)

    def _execute(self, context):
        if not self.document or not self.object:
            self.report({"ERROR"}, "Invalid document or object")
            return

        document = tool.Ifc.get().by_id(self.document)
        product = tool.Ifc.get().by_id(self.object)

        if document and product:
            tool.Ifc.run("document.unassign_document", products=[product], document=document)

            # Refresh document data after removal
            ObjectDocumentData.load()
            DocumentData.load()
            props = tool.Document.get_document_props()
            tool.Document.load_referenceable_objects(document)

            self.report({"INFO"}, f"Removed object from document")


class OpenIFCDocument(bpy.types.Operator):
    bl_idname = "bim.open_ifc_document"
    bl_label = "Open IFC Document"
    bl_description = "Open the IFC document in a new Blender instance and load the project"
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
