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
from bonsai.bim.module.document.data import DocumentData, ObjectDocumentData


def update_document_objects(document_id=None):
    DocumentData.is_loaded = False
    DocumentData.load()
    
    # If no specific document_id is provided, try to get it from the active document
    if document_id is None:
        props = tool.Document.get_document_props()
        if props.documents and props.active_document_index < len(props.documents):
            document = props.documents[props.active_document_index]
            if document.ifc_definition_id:
                document_id = document.ifc_definition_id
    
    # Update objects for the document if an ID is available
    if document_id:
        DocumentData.load_document_objects_into_props(document_id)


class LoadProjectDocuments(bpy.types.Operator):
    bl_idname = "bim.load_project_documents"
    bl_label = "Load Project Documents"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        core.load_project_documents(tool.Document)
        bonsai.bim.handler.refresh_ui_data()  # Update breadcrumbs data.
        update_document_objects()
        return {"FINISHED"}


class LoadDocument(bpy.types.Operator):
    bl_idname = "bim.load_document"
    bl_label = "Load Document"
    bl_options = {"REGISTER", "UNDO"}
    document: bpy.props.IntProperty()

    def execute(self, context):
        core.load_document(tool.Document, document=tool.Ifc.get().by_id(self.document))
        bonsai.bim.handler.refresh_ui_data()  # Update breadcrumbs data.
        update_document_objects()
        return {"FINISHED"}


class LoadParentDocument(bpy.types.Operator):
    bl_idname = "bim.load_parent_document"
    bl_label = "Load Parent Document"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        core.load_parent_document(tool.Document)
        bonsai.bim.handler.refresh_ui_data()  # Update breadcrumbs data.
        update_document_objects()
        return {"FINISHED"}



class DisableDocumentEditingUI(bpy.types.Operator):
    bl_idname = "bim.disable_document_editing_ui"
    bl_label = "Disable Document Editing UI"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        core.disable_document_editing_ui(tool.Document)
        return {"FINISHED"}

class DisableObjectDocumentEditingUI(bpy.types.Operator):
    bl_idname = "bim.disable_object_document_editing_ui"
    bl_label = "Disable Object Document Editing UI"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = tool.Document.get_document_props()
        props.is_object_editing = False
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
        if props.active_document_id:
            core.edit_document(tool.Ifc, tool.Document, document=tool.Ifc.get().by_id(props.active_document_id))
            props.active_document_id = 0
            DocumentData.is_loaded = False
            DocumentData.load()
            ObjectDocumentData.is_loaded = False  
            ObjectDocumentData.load()
            bpy.ops.bim.update_assigned_documents()
            bonsai.bim.handler.refresh_ui_data()




class RemoveDocument(bpy.types.Operator, tool.Ifc.Operator):
    bl_idname = "bim.remove_document"
    bl_label = "Remove Document"
    bl_options = {"REGISTER", "UNDO"}
    document: bpy.props.IntProperty()

    def _execute(self, context):
        core.remove_document(tool.Ifc, tool.Document, document=tool.Ifc.get().by_id(self.document))

class UpdateAssignedDocuments(bpy.types.Operator):
    bl_idname = "bim.update_assigned_documents"
    bl_label = "Update Assigned Documents"
    bl_description = "Update the list of documents assigned to the active object"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        # Make sure we're working with the latest data
        ObjectDocumentData.is_loaded = False
        ObjectDocumentData.load()
            
        # Populate the properties collection
        props = tool.Document.get_document_props()
        props.assigned_documents.clear()
        
        if not ObjectDocumentData.data.get("documents"):
            return {"FINISHED"}
        
        # Sort documents by identification then name
        sorted_docs = sorted(
            ObjectDocumentData.data["documents"], 
            key=lambda doc: ((doc.get("identification") or "").lower(), 
                           (doc.get("name") or "").lower())
        )
        
        for document in sorted_docs:
            new = props.assigned_documents.add()
            new.name = document["name"] or "Unnamed"
            new.identification = document["identification"] or "*"
            new.is_information = document.get("is_information", False)
            new.ifc_definition_id = document["id"]
            # Ensure location is properly set
            new.location = document.get("location") or ""
            new.description = document.get("description") or ""
            
        return {"FINISHED"}

class AssignDocument(bpy.types.Operator, tool.Ifc.Operator):
    bl_idname = "bim.assign_document"
    bl_label = "Assign Document"
    bl_description = "Assign active document to the selected objects."
    bl_options = {"REGISTER", "UNDO"}
    obj: bpy.props.StringProperty()
    document: bpy.props.IntProperty()

    def _execute(self, context):
        # Get the document to assign
        document = tool.Ifc.get().by_id(self.document)
        
        # Get the objects to assign it to
        objs = [bpy.data.objects[self.obj]] if self.obj else tool.Blender.get_selected_objects()
        
        for obj in objs:
            element = tool.Ifc.get_entity(obj)
            if element:
                core.assign_document(tool.Ifc, product=element, document=document)
        
        # Update document objects for the assigned document
        update_document_objects(self.document)
        
        # Refresh object document data
        ObjectDocumentData.is_loaded = False
        ObjectDocumentData.load()
        bpy.ops.bim.update_assigned_documents()


class UnassignDocument(bpy.types.Operator, tool.Ifc.Operator):
    bl_idname = "bim.unassign_document"
    bl_label = "Unassign Document"
    bl_options = {"REGISTER", "UNDO"}
    obj: bpy.props.StringProperty()
    document: bpy.props.IntProperty()

    def _execute(self, context):
        # Get the document to unassign
        document = tool.Ifc.get().by_id(self.document)
        
        # Get the objects to unassign it from
        objs = [bpy.data.objects.get(self.obj)] if self.obj else tool.Blender.get_selected_objects()
        for obj in objs:
            element = tool.Ifc.get_entity(obj)
            if element:
                import bonsai.core.document as core
                core.unassign_document(tool.Ifc, product=element, document=document)
        
        # Get the currently active document in BIM_UL_documents
        props = tool.Document.get_document_props()
        active_document_id = None
        if props.documents and props.active_document_index < len(props.documents):
            active_document = props.documents[props.active_document_index]
            active_document_id = active_document.ifc_definition_id
            
        # Update the document objects list with objects from the ACTIVE document,
        # not the one being unassigned (if they're different)
        if active_document_id and active_document_id != self.document:
            update_document_objects(active_document_id)
        else:
            # If there's no active document or it's the same as the one being unassigned,
            # then update the objects for the unassigned document
            update_document_objects(self.document)
        
        # Reload the ObjectDocumentData to reflect the removed assignment
        ObjectDocumentData.is_loaded = False
        ObjectDocumentData.load()
        
        # Update the assigned documents list in the UI
        bpy.ops.bim.update_assigned_documents()

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


class LoadObjectDocuments(bpy.types.Operator):
    bl_idname = "bim.load_object_documents"
    bl_label = "Load Object Documents"
    bl_description = "Load documents to assign to the selected object"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        # First make sure ObjectDocumentData is loaded
        if not ObjectDocumentData.is_loaded:
            ObjectDocumentData.load()
            
        # Load project documents for selection
        core.load_project_documents(tool.Document)
        
        # Set editing mode
        props = tool.Document.get_document_props()
        props.is_object_editing = True
        
        # Update UI breadcrumbs
        bonsai.bim.handler.refresh_ui_data()
        
        # Update the assigned documents list
        self.update_assigned_documents(props)
        
        return {"FINISHED"}
    
    def update_assigned_documents(self, props):
        # Clear existing assigned documents
        props.assigned_documents.clear()
        
        # Get document data
        if not ObjectDocumentData.data.get("documents"):
            return
            
        # Sort documents by identification then name
        sorted_docs = sorted(
            ObjectDocumentData.data["documents"], 
            key=lambda doc: ((doc.get("identification") or "").lower(), 
                           (doc.get("name") or "").lower())
        )
        
        # Add documents to the collection
        for document in sorted_docs:
            new = props.assigned_documents.add()
            new.name = document["name"] or "Unnamed"
            new.identification = document["identification"] or "*"
            new.is_information = document.get("is_information", False)
            new.ifc_definition_id = document["id"] 
            new.location = document["location"] or ""
            new.description = document["description"] or ""

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

class ToggleDocument(bpy.types.Operator, tool.Ifc.Operator):
    bl_idname = "bim.toggle_document"
    bl_label = "Toggle Document"
    bl_options = {"REGISTER", "UNDO"}
    document: bpy.props.IntProperty()
    option: bpy.props.StringProperty()

    def _execute(self, context):
        import json
        expanded_documents = []
        try:
            expanded_documents = json.loads(context.scene.ExpandedDocuments.json_string)
        except (AttributeError, json.JSONDecodeError):
            expanded_documents = []
            
        document_id = self.document
        
        if self.option == "Expand" and document_id not in expanded_documents:
            expanded_documents.append(document_id)
        elif self.option == "Collapse" and document_id in expanded_documents:
            expanded_documents.remove(document_id)
            
        context.scene.ExpandedDocuments.json_string = json.dumps(expanded_documents)
        
        # Reload documents with updated expand/collapse state
        bpy.ops.bim.load_project_documents()
        return {"FINISHED"}