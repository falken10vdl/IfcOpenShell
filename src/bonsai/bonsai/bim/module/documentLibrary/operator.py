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
import ifcopenshell
import bonsai.bim.handler
import bonsai.tool as tool
import bonsai.core.documentLibrary as core
from .data import DocumentLibraryData, ObjectDocumentLibraryData


def update_library_objects(library_id=None):
    DocumentLibraryData.is_loaded = False
    DocumentLibraryData.load()
    
    if library_id is None:
        props = tool.DocumentLibrary.get_library_props()
        if props.libraries and props.active_library_index < len(props.libraries):
            document_id = props.libraries[props.active_library_index].ifc_definition_id
            DocumentLibraryData.load_library_objects_into_props(document_id)
    
    if library_id:
        DocumentLibraryData.load_library_objects_into_props(library_id)


class LoadProjectLibraries(bpy.types.Operator):
    bl_idname = "bim.load_project_document_libraries"
    bl_label = "Load Project Libraries"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        core.load_project_document_libraries(tool.DocumentLibrary)
        update_library_objects()
        return {"FINISHED"}


class LoadLibrary(bpy.types.Operator):
    bl_idname = "bim.load_library"
    bl_label = "Load Library"
    bl_options = {"REGISTER", "UNDO"}
    library: bpy.props.IntProperty()

    def execute(self, context):
        core.load_library(tool.DocumentLibrary, library=tool.Ifc.get().by_id(self.library))
        bonsai.bim.handler.refresh_ui_data()
        update_library_objects()
        return {"FINISHED"}


class DisableLibraryEditingUI(bpy.types.Operator):
    bl_idname = "bim.disable_library_editing_ui"
    bl_label = "Disable Library Editing UI"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        core.disable_library_editing_ui(tool.DocumentLibrary)
        return {"FINISHED"}


class DisableObjectLibraryEditingUI(bpy.types.Operator):
    bl_idname = "bim.disable_object_library_editing_ui"
    bl_label = "Disable Object Library Editing UI"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = tool.DocumentLibrary.get_library_props()
        props.is_object_editing = False
        return {"FINISHED"}


class EnableEditingDocumentLibrary(bpy.types.Operator):
    bl_idname = "bim.enable_editing_document_library"
    bl_label = "Enable Editing Library"
    bl_options = {"REGISTER", "UNDO"}
    library: bpy.props.IntProperty()

    def execute(self, context):
        props = tool.DocumentLibrary.get_library_props()
        props.is_library_editing = True
        core.enable_editing_library(tool.DocumentLibrary, library=tool.Ifc.get().by_id(self.library))
        return {"FINISHED"}


class DisableEditingLibrary(bpy.types.Operator):
    bl_idname = "bim.disable_editing_document_library"
    bl_label = "Disable Editing Library"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = tool.DocumentLibrary.get_library_props()
        props.is_library_editing = False
        core.disable_editing_library(tool.DocumentLibrary)
        return {"FINISHED"}


class AddInformation(bpy.types.Operator, tool.Ifc.Operator):
    bl_idname = "bim.add_library_information"
    bl_label = "Add Information"
    bl_options = {"REGISTER", "UNDO"}

    def _execute(self, context):
        props = tool.DocumentLibrary.get_library_props()
        
        parent = None
        if props.libraries and props.active_library_index < len(props.libraries):
            selected_item = props.libraries[props.active_library_index]
            if selected_item.is_information and selected_item.ifc_definition_id != -1:
                parent = tool.Ifc.get().by_id(selected_item.ifc_definition_id)
        
        information = core.add_library_information(tool.Ifc, tool.DocumentLibrary)
        
        # Update expanded libraries state
        import json
        expanded_libs = []
        try:
            expanded_libs = json.loads(context.scene.ExpandedLibraries.json_string)
        except (AttributeError, json.JSONDecodeError):
            pass
        
        # Ensure the root and parent are expanded
        project = tool.Ifc.get().by_type("IfcProject")[0]
        virtual_root_id = -project.id()
        if virtual_root_id in expanded_libs:
            expanded_libs.append(virtual_root_id)
                
        context.scene.ExpandedLibraries.json_string = json.dumps(expanded_libs)
        
        bpy.ops.bim.load_project_document_libraries()
        
        return {"FINISHED"}


class AddLibraryReference(bpy.types.Operator, tool.Ifc.Operator):
    bl_idname = "bim.add_document_library_reference"
    bl_label = "Add Library Reference"
    bl_options = {"REGISTER", "UNDO"}

    def _execute(self, context):
        props = tool.DocumentLibrary.get_library_props()
        
        if not props.libraries or props.active_library_index >= len(props.libraries):
            self.report({"ERROR"}, "No library selected")
            return {"CANCELLED"}
            
        selected_library = props.libraries[props.active_library_index]
        
        if not selected_library.is_information:
            self.report({"ERROR"}, "Cannot add a reference to a reference element")
            return {"CANCELLED"}
            
        parent = tool.Ifc.get().by_id(selected_library.ifc_definition_id)
        
        # Clear any previous library attributes to avoid data persistence
        props.library_attributes.clear()
        
        # Store the current editing states
        was_editing = props.is_editing
        was_library_editing = props.is_library_editing
        
        # Add the reference using the core function
        core.add_library_reference(tool.Ifc, tool.DocumentLibrary)
        
        # Restore editing states
        props.is_editing = was_editing
        props.is_library_editing = was_library_editing
        
        # Update expanded libraries state
        import json
        expanded_libs = []
        try:
            expanded_libs = json.loads(context.scene.ExpandedLibraries.json_string)
        except (AttributeError, json.JSONDecodeError):
            pass
            
        if parent.id() not in expanded_libs:
            expanded_libs.append(parent.id())
            context.scene.ExpandedLibraries.json_string = json.dumps(expanded_libs)
        
        # Reload documents with updated state
        bpy.ops.bim.load_project_document_libraries()
        
        return {"FINISHED"}


class EditDocumentLibrary(bpy.types.Operator, tool.Ifc.Operator):
    bl_idname = "bim.edit_document_library"
    bl_label = "Edit Information"
    bl_options = {"REGISTER", "UNDO"}

    def _execute(self, context):
        props = tool.DocumentLibrary.get_library_props()
        if props.active_library_id:
            core.edit_library(tool.Ifc, tool.DocumentLibrary, library=tool.Ifc.get().by_id(props.active_library_id))
            props.active_library_id = 0
            props.is_library_editing = False
            DocumentLibraryData.is_loaded = False
            DocumentLibraryData.load()
            ObjectDocumentLibraryData.is_loaded = False  
            ObjectDocumentLibraryData.load()
            bpy.ops.bim.update_assigned_libraries()
            bonsai.bim.handler.refresh_ui_data()
            return {"FINISHED"}


class RemoveDocumentLibrary(bpy.types.Operator, tool.Ifc.Operator):
    bl_idname = "bim.remove_document_library"
    bl_label = "Remove Library"
    bl_options = {"REGISTER", "UNDO"}
    library: bpy.props.IntProperty()

    def _execute(self, context):
        core.remove_library(tool.Ifc, tool.DocumentLibrary, library=tool.Ifc.get().by_id(self.library))
        return {"FINISHED"}


class UpdateAssignedLibraries(bpy.types.Operator):
    bl_idname = "bim.update_assigned_libraries"
    bl_label = "Update Assigned Libraries"
    bl_description = "Update the list of libraries assigned to the active object"
    bl_options = {"REGISTER"}
    
    def execute(self, context):
        ObjectDocumentLibraryData.is_loaded = False
        ObjectDocumentLibraryData.load()
            
        props = tool.DocumentLibrary.get_library_props()
        props.assigned_libraries.clear()
        
        if not ObjectDocumentLibraryData.data.get("libraries"):
            return {"FINISHED"}
        
        sorted_libs = sorted(
            ObjectDocumentLibraryData.data["libraries"], 
            key=lambda lib: ((lib.get("identification", "") or "").lower(), 
                        (lib.get("name") or "").lower())
        )
        
        for library in sorted_libs:
            lib = props.assigned_libraries.add()
            lib.ifc_definition_id = library["id"]
            lib.name = library["name"] or ""
            if "identification" in library:
                lib.identification = library["identification"] or ""
            lib.is_information = library["is_information"]
            lib.location = library["location"] or ""
            lib.description = library["description"] or ""
        
        return {"FINISHED"}


class AssignLibrary(bpy.types.Operator, tool.Ifc.Operator):
    bl_idname = "bim.assign_library"
    bl_label = "Assign Library"
    bl_description = "Assign active library to the selected objects."
    bl_options = {"REGISTER", "UNDO"}
    obj: bpy.props.StringProperty()
    library: bpy.props.IntProperty()

    def _execute(self, context):
        library = tool.Ifc.get().by_id(self.library)
        
        objs = [bpy.data.objects[self.obj]] if self.obj else tool.Blender.get_selected_objects()
        
        for obj in objs:
            element = tool.Ifc.get_entity(obj)
            if element:
                core.assign_library(tool.Ifc, element, library)
        
        update_library_objects(self.library)
        
        ObjectDocumentLibraryData.is_loaded = False
        ObjectDocumentLibraryData.load()
        bpy.ops.bim.update_assigned_libraries()
        return {"FINISHED"}


class UnassignLibrary(bpy.types.Operator, tool.Ifc.Operator):
    bl_idname = "bim.unassign_library"
    bl_label = "Unassign Library"
    bl_options = {"REGISTER", "UNDO"}
    obj: bpy.props.StringProperty()
    library: bpy.props.IntProperty()

    def _execute(self, context):
        library = tool.Ifc.get().by_id(self.library)
        
        objs = [bpy.data.objects.get(self.obj)] if self.obj else tool.Blender.get_selected_objects()
        for obj in objs:
            if obj:
                element = tool.Ifc.get_entity(obj)
                if element:
                    core.unassign_library(tool.Ifc, element, library)
        
        props = tool.DocumentLibrary.get_library_props()
        active_library_id = None
        if props.libraries and props.active_library_index < len(props.libraries):
            active_library_id = props.libraries[props.active_library_index].ifc_definition_id

        if active_library_id and active_library_id != self.library:
            update_library_objects(active_library_id)
        else:
            update_library_objects()
        
        ObjectDocumentLibraryData.is_loaded = False
        ObjectDocumentLibraryData.load()
        
        bpy.ops.bim.update_assigned_libraries()
        return {"FINISHED"}


class SelectLibraryObjects(bpy.types.Operator):
    bl_idname = "bim.select_library_objects"
    bl_label = "Select Library Objects"
    bl_options = {"REGISTER", "UNDO"}
    library: bpy.props.IntProperty(name="Library ID", default=0)

    def execute(self, context):
        if not self.library or not (relating_library := tool.Ifc.get_entity_by_id(self.library)):
            self.report({"ERROR"}, "Library not found")
            return {"CANCELLED"}

        i = 0
        for element in ifcopenshell.util.element.get_referenced_elements(relating_library):
            obj = tool.Ifc.get_object(element)
            if obj:
                obj.select_set(True)
                i += 1
                
        self.report({"INFO"}, f"{i} objects selected.")
        return {"FINISHED"}


class LoadObjectLibraries(bpy.types.Operator):
    bl_idname = "bim.load_object_libraries"
    bl_label = "Load Object Libraries"
    bl_description = "Load libraries to assign to the selected object"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        if not ObjectDocumentLibraryData.is_loaded:
            ObjectDocumentLibraryData.load()
            
        core.load_project_document_libraries(tool.DocumentLibrary)
        
        props = tool.DocumentLibrary.get_library_props()
        props.is_object_editing = True
        
        bonsai.bim.handler.refresh_ui_data()
        
        self.update_assigned_libraries(props)
        
        return {"FINISHED"}
    
    def update_assigned_libraries(self, props):
        props.assigned_libraries.clear()
        
        if not ObjectDocumentLibraryData.data.get("libraries"):
            return
            
        for library in ObjectDocumentLibraryData.data["libraries"]:
            lib = props.assigned_libraries.add()
            lib.ifc_definition_id = library["id"]
            lib.name = library["name"] or ""
            if "identification" in library:
                lib.identification = library["identification"] or ""
            lib.is_information = library["is_information"]
            lib.location = library["location"] or ""
            lib.description = library["description"] or ""


class OpenIFCLibrary(bpy.types.Operator):
    bl_idname = "bim.open_ifc_library"
    bl_label = "Open IFC Library"
    bl_description = "Open the IFC library in a new Blender instance and load the project"
    bl_options = {"REGISTER", "UNDO"}

    uri: bpy.props.StringProperty(name="URI")

    def execute(self, context):
        import subprocess
        import sys
        import os

        if not self.uri or not self.uri.lower().startswith("file://"):
            self.report({"ERROR"}, "Only local file:// URIs are supported")
            return {"CANCELLED"}

        filepath = self.uri[7:]  # Remove file:// prefix
        
        if not os.path.exists(filepath):
            self.report({"ERROR"}, f"File not found: {filepath}")
            return {"CANCELLED"}

        # Launch Blender with the IFC file
        blender_path = bpy.app.binary_path
        args = [blender_path, "--python-expr", "import bpy; bpy.ops.bim.load_project(filepath='{}')".format(filepath)]
        
        subprocess.Popen(args)
        self.report({"INFO"}, f"Opening {filepath} in a new Blender instance")
        return {"FINISHED"}


class ToggleLibrary(bpy.types.Operator, tool.Ifc.Operator):
    bl_idname = "bim.toggle_library"
    bl_label = "Toggle Library"
    bl_options = {"REGISTER", "UNDO"}
    library: bpy.props.IntProperty()
    option: bpy.props.StringProperty()

    def _execute(self, context):
        if not context.scene.ExpandedLibraries:
            return {"CANCELLED"}
            
        # Get current expanded libraries
        expanded_libs = []
        try:
            expanded_libs = json.loads(context.scene.ExpandedLibraries.json_string)
        except (AttributeError, json.JSONDecodeError):
            pass
            
        # Toggle expanded state
        if self.library in expanded_libs and self.option == "Collapse":
            expanded_libs.remove(self.library)
        elif self.library not in expanded_libs and self.option == "Expand":
            expanded_libs.append(self.library)
            
        # Save expanded state
        context.scene.ExpandedLibraries.json_string = json.dumps(expanded_libs)
        
        # Refresh UI
        core.load_project_document_libraries(tool.DocumentLibrary)
        return {"FINISHED"}


class UnselectLibrary(bpy.types.Operator):
    bl_idname = "bim.unselect_library"
    bl_label = "Unselect Library"
    bl_options = {"REGISTER", "UNDO"}
    
    def execute(self, context):
        props = tool.DocumentLibrary.get_library_props()
        props.active_library_index = -1
        return {'FINISHED'}
