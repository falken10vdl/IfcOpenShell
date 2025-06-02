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

def load_project_document_libraries(document_library: tool.DocumentLibrary) -> None:
    """Load top-level document libraries (similar to load_project_documents)."""
    document_library.clear_document_library_tree()
    document_library.import_project_document_libraries()
    document_library.enable_document_library_editing_ui()

def load_document_library(document_library_tool: tool.DocumentLibrary, doclib_entity: ifcopenshell.entity_instance) -> None:
    """Load the sub-libraries and references for the given document library entity."""
    document_library_tool.clear_document_library_tree()
    document_library_tool.import_sublibraries(doclib_entity)
    document_library_tool.import_references(doclib_entity)
    document_library_tool.disable_editing_document_library()
    document_library_tool.add_breadcrumb(doclib_entity)

def load_parent_document_library(document_library: tool.DocumentLibrary) -> None:
    """Load the parent library from the breadcrumb trail (similar to load_parent_document)."""
    document_library.clear_document_library_tree()
    
    document_library.remove_latest_breadcrumb()
    
    parent = document_library.get_active_breadcrumb()
    
    if parent:
        print(f"Loading parent document library: {parent.id()}")
        document_library.import_sublibraries(parent)
        document_library.import_references(parent)
        document_library.disable_editing_document_library()
    else:
        document_library.import_project_document_libraries()

def disable_document_library_editing_ui(document_library: tool.DocumentLibrary) -> None:
    """Disable the UI editing state."""
    document_library.disable_document_library_editing_ui()
    document_library.disable_editing_document_library()

def enable_editing_document_library(document_library_tool: tool.DocumentLibrary, doclib_entity: ifcopenshell.entity_instance) -> None:
    """Enable editing mode for a specific document library entity."""
    document_library_tool.import_document_library_attributes(doclib_entity)
    document_library_tool.load_referenceable_objects(doclib_entity)
    document_library_tool.set_active_document_library(doclib_entity)

def disable_editing_document_library(document_library: tool.DocumentLibrary) -> None:
    """Disable editing for the currently active document library."""
    document_library.set_inactive_document_library()

def add_library_information(ifc: tool.Ifc, document_library: tool.DocumentLibrary) -> None:
    """Add a new library information entity, either at the root or nested under current active library."""
    parent = document_library.get_active_breadcrumb()
    library_info = ifc.run("library.add_information", parent=parent)
    
    document_library.clear_document_library_tree()
    
    if parent:
        document_library.import_sublibraries(parent)
        document_library.import_references(parent)
    else:
        document_library.import_project_document_libraries()
    

def add_library_reference(ifc: tool.Ifc, document_library: tool.DocumentLibrary) -> None:
    parent = document_library.get_active_breadcrumb()
    assert parent, "Parent library must exist to add a reference"
    ifc.run("library.add_reference", library=parent)
    document_library.clear_document_library_tree()
    document_library.import_sublibraries(parent)
    document_library.import_references(parent)

def edit_document_library(ifc: tool.Ifc, document_library_tool: tool.DocumentLibrary, doclib_entity: ifcopenshell.entity_instance) -> None:
    """Edit a document library entity and update any selected object references."""
    attributes = document_library_tool.export_document_library_attributes()
    if document_library_tool.is_library_information(doclib_entity):
        ifc.run("library.edit_information", information=doclib_entity, attributes=attributes)
    else:
        ifc.run("library.edit_reference", reference=doclib_entity, attributes=attributes)

    props = document_library_tool.get_document_library_props()
    for obj in props.document_library_referenced_objects:
        if obj.is_selected:
            product = ifc.get().by_id(obj.ifc_definition_id)
            assign_document_library(ifc, product, doclib_entity)

    document_library_tool.disable_editing_document_library()
    document_library_tool.clear_document_library_tree()
    parent = document_library_tool.get_active_breadcrumb()
    if parent:
        document_library_tool.import_sublibraries(parent)
        document_library_tool.import_references(parent)
    else:
        document_library_tool.import_project_document_libraries()

def remove_document_library(ifc: tool.Ifc, document_library_tool: tool.DocumentLibrary, doclib_entity: ifcopenshell.entity_instance) -> None:
    document_library_tool.clear_document_library_tree()
    if document_library_tool.is_library_information(doclib_entity):
        ifc.run("library.remove_information", information=doclib_entity)
    else:
        ifc.run("library.remove_reference", reference=doclib_entity)
    parent = document_library_tool.get_active_breadcrumb()
    if parent:
        document_library_tool.import_sublibraries(parent)
        document_library_tool.import_references(parent)
    else:
        document_library_tool.import_project_document_libraries()

def assign_document_library(
    ifc: tool.Ifc, product: ifcopenshell.entity_instance, doclib_entity: ifcopenshell.entity_instance
) -> None:
    ifc.run("library.assign_library", products=[product], library=doclib_entity)

def unassign_document_library(
    ifc: tool.Ifc, product: ifcopenshell.entity_instance, doclib_entity: ifcopenshell.entity_instance
) -> None:
    ifc.run("library.unassign_library", products=[product], library=doclib_entity)
