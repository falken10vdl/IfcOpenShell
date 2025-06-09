# Bonsai - OpenBIM Blender Add-on
# Copyright (C) 2022 Dion Moult <dion@thinkmoult.com>
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
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import bpy
    import ifcopenshell
    import bonsai.tool as tool


def load_project_document_libraries(DocumentLibrary: tool.DocumentLibrary) -> None:
    DocumentLibrary.clear_library_tree()
    DocumentLibrary.import_project_libraries()
    DocumentLibrary.enable_editing_ui()

def load_library(DocumentLibrary_tool: tool.DocumentLibrary, library: ifcopenshell.entity_instance) -> None:
    DocumentLibrary_tool.clear_library_tree()
    
    # Update the expanded libraries list to ensure this library is expanded
    import bpy, json
    try:
        expanded_libs = json.loads(bpy.context.scene.ExpandedLibraries.json_string)
    except (AttributeError, json.JSONDecodeError):
        expanded_libs = []
        
    # Ensure the library is expanded
    if library.id() not in expanded_libs:
        expanded_libs.append(library.id())
        bpy.context.scene.ExpandedLibraries.json_string = json.dumps(expanded_libs)
    
    # Reload all libraries with proper tree structure
    DocumentLibrary_tool.import_project_libraries()
    DocumentLibrary_tool.disable_editing_library()

def disable_library_editing_ui(DocumentLibrary: tool.DocumentLibrary) -> None:
    DocumentLibrary.disable_editing_ui()
    DocumentLibrary.disable_editing_library()

def enable_editing_library(DocumentLibrary_tool: tool.DocumentLibrary, library: ifcopenshell.entity_instance) -> None:
    props = DocumentLibrary_tool.get_library_props()
    props.active_library_id = library.id()
    props.is_library_editing = True
    DocumentLibrary_tool.import_library_attributes(library)

def disable_editing_library(DocumentLibrary: tool.DocumentLibrary) -> None:
    props = DocumentLibrary.get_library_props()
    props.active_library_id = 0
    props.is_library_editing = False
    props.library_attributes.clear()


def add_library_information(ifc: tool.Ifc, DocumentLibrary_tool: tool.DocumentLibrary) -> ifcopenshell.entity_instance:
    """Add a new library information to the project
    
    Args:
        ifc: The IFC tool
        DocumentLibrary_tool: The DocumentLibrary tool
        
    Returns:
        The newly created library information
    """
    DocumentLibrary_tool.clear_library_tree()
    
    # Create the information using the IFC API
    information = ifc.run("library.add_library", name="Unnamed")
    
    # Reload project libraries to update UI
    DocumentLibrary_tool.import_project_libraries()
        
    return information

def add_library_reference(ifc: tool.Ifc, DocumentLibrary: tool.DocumentLibrary) -> None:
    props = DocumentLibrary.get_library_props()
    parent = None
    
    if props.libraries and props.active_library_index < len(props.libraries):
        selected_library = props.libraries[props.active_library_index]
        if selected_library.is_information:
            parent = ifc.get().by_id(selected_library.ifc_definition_id)
    
    if parent:
        # Create the reference
        reference = ifc.run("library.add_reference", library=parent)
        
        # Explicitly ensure Location is initialized to empty string
        reference.Location = ""
        
        # Update expanded libraries list to ensure parent is expanded to show the new reference
        import bpy, json
        try:
            expanded_libs = json.loads(bpy.context.scene.ExpandedLibraries.json_string)
        except (AttributeError, json.JSONDecodeError):
            expanded_libs = []
            
        # Ensure the parent is expanded
        if parent.id() not in expanded_libs:
            expanded_libs.append(parent.id())
            bpy.context.scene.ExpandedLibraries.json_string = json.dumps(expanded_libs)

    DocumentLibrary.import_project_libraries()

def edit_library(ifc: tool.Ifc, DocumentLibrary_tool: tool.DocumentLibrary, library: ifcopenshell.entity_instance) -> None:
    attributes = DocumentLibrary_tool.export_library_attributes()
    if DocumentLibrary_tool.is_library_information(library):
        ifc.run("library.edit_library", library=library, attributes=attributes)
    else:
        ifc.run("library.edit_reference", reference=library, attributes=attributes)
    DocumentLibrary_tool.disable_editing_library()
    DocumentLibrary_tool.clear_library_tree()
    DocumentLibrary_tool.import_project_libraries()

def remove_library(ifc: tool.Ifc, DocumentLibrary_tool: tool.DocumentLibrary, library: ifcopenshell.entity_instance) -> None:
    DocumentLibrary_tool.clear_library_tree()
    if DocumentLibrary_tool.is_library_information(library):
        ifc.run("library.remove_library", library=library)
    else:
        ifc.run("library.remove_reference", reference=library)
    DocumentLibrary_tool.import_project_libraries()


def assign_library(ifc, product, library):
    """Assign a library to a product
    
    Args:
        ifc: The IFC tool
        product: The IFC product entity
        library: The IfcLibraryInformation or IfcLibraryReference entity
    """
    if library.is_a("IfcLibraryInformation"):
        # For IfcLibraryInformation, use the library assignment function
        ifc.run("library.assign_library", products=[product], library=library)
    elif library.is_a("IfcLibraryReference"):
        # For IfcLibraryReference, use the reference assignment function
        ifc.run("library.assign_reference", products=[product], reference=library)
    else:
        raise ValueError(f"Unsupported library type: {library.is_a()}")

def unassign_library(ifc, product, library):
    """Unassign a library from a product
    
    Args:
        ifc: The IFC tool
        product: The IFC product entity
        library: The IfcLibraryInformation or IfcLibraryReference entity
    """
    if library.is_a("IfcLibraryInformation"):
        # For IfcLibraryInformation, use the library unassignment function
        ifc.run("library.unassign_library", products=[product], library=library)
    elif library.is_a("IfcLibraryReference"):
        # For IfcLibraryReference, use the reference unassignment function
        ifc.run("library.unassign_reference", products=[product], reference=library)
    else:
        raise ValueError(f"Unsupported library type: {library.is_a()}")

