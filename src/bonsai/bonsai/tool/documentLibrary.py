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
import bpy
import ifcopenshell.util.system
import bonsai.bim.helper
import bonsai.core.tool
import bonsai.tool as tool
from typing import Any, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from bonsai.bim.module.documentLibrary.prop import BIMDocumentLibraryProperties


class DocumentLibrary(bonsai.core.tool.DocumentLibrary):
    @classmethod
    def get_library_props(cls) -> BIMDocumentLibraryProperties:
        return bpy.context.scene.BIMDocumentLibraryProperties

    @classmethod
    def clear_library_tree(cls) -> None:
        props = cls.get_library_props()
        props.libraries.clear()

    @classmethod
    def disable_editing_library(cls) -> None:
        props = cls.get_library_props()
        props.active_library_id = 0

    @classmethod
    def disable_editing_ui(cls) -> None:
        props = cls.get_library_props()
        props.is_editing = False

    @classmethod
    def enable_editing_ui(cls) -> None:
        props = cls.get_library_props()
        props.is_editing = True

    @classmethod
    def export_library_attributes(cls) -> dict[str, Any]:
        props = cls.get_library_props()
        return bonsai.bim.helper.export_attributes(props.library_attributes)

    @classmethod
    def import_library_attributes(cls, library: ifcopenshell.entity_instance) -> None:
        props = cls.get_library_props()
        props.library_attributes.clear()

        def callback(attr_name: str, attr_value: Any, data: dict[str, Any]) -> Union[bool, None]:
            if attr_name == "Location" and attr_value is None:
                # Always ensure Location has a default empty string value
                data[attr_name] = ""
                return True
                
            if attr_name != "Name":
                return None  # Proceed normally

            current_value = data[attr_name]
            # If Name is already filled, display it so user would be able to correct invalid IFC.
            if current_value is not None:
                return None

            # Skip import since IFC restricts Name to be filled
            # for IfcLibraryReference with ReferencedLibrary.
            return False

        import_callback = callback if library.is_a("IfcLibraryReference") else None
        bonsai.bim.helper.import_attributes2(library, props.library_attributes, callback=import_callback)

    @classmethod
    def import_project_libraries(cls) -> None:
        """Import all libraries in the project using a simplified approach
        
        - All IfcLibraryInformation elements are direct children of IfcProject
        - All IfcLibraryReference elements are children of IfcLibraryInformation
        """
        props = cls.get_library_props()
        props.libraries.clear()
        file = tool.Ifc.get()
        
        # Get expanded libraries state
        import json
        expanded_libraries = []
        try:
            expanded_libraries = json.loads(bpy.context.scene.ExpandedLibraries.json_string)
        except (AttributeError, json.JSONDecodeError):
            pass
                
        # Get the project
        project = file.by_type("IfcProject")[0] if file.by_type("IfcProject") else None
        if not project:
            return
        
        # Create library info to reference mapping
        library_children = {}
        
        # Find all library references and link them to their parent libraries
        for ref in file.by_type("IfcLibraryReference"):
            parent = None
            
            # Schema-specific parent lookup
            if file.schema == "IFC2X3":
                # In IFC2X3, the inverse attribute LibraryReference holds the parent
                if hasattr(ref, "LibraryReference") and ref.LibraryReference:
                    parent = ref.LibraryReference[0]
            else:
                # In IFC4, the direct attribute ReferencedLibrary holds the parent
                if hasattr(ref, "ReferencedLibrary") and ref.ReferencedLibrary:
                    parent = ref.ReferencedLibrary
            
            # If parent is found, add to children map
            if parent and parent.is_a("IfcLibraryInformation"):
                parent_id = parent.id()
                if parent_id not in library_children:
                    library_children[parent_id] = []
                library_children[parent_id].append(ref)
        
        # Get all library information elements
        library_infos = file.by_type("IfcLibraryInformation")
        
        # Create virtual root element
        root = props.libraries.add()
        root.ifc_definition_id = -1
        root.is_information = True
        root.name = f"Project Libraries ({project.Name or 'Unnamed Project'})"
        root.identification = ""
        root.location = ""
        root.tree_depth = 0
        root.has_children = bool(library_infos)
        
        # Set root expansion state
        root_id = -project.id()
        root.is_expanded = root_id not in expanded_libraries
        
        # If root is expanded, add all library information elements
        if root.is_expanded and library_infos:
            # Sort library information elements
            library_infos.sort(key=lambda lib: (
                (cls.get_library_information_id(lib) or "").lower(),
                (lib.Name or "").lower()
            ))
            
            # Add each library information element
            for lib_info in library_infos:
                # Add the library information
                info_item = props.libraries.add()
                info_item.ifc_definition_id = lib_info.id()
                info_item.is_information = True
                info_item.tree_depth = 1
                info_item.name = lib_info.Name or "Unnamed"
                info_item.identification = cls.get_library_information_id(lib_info) or ""
                info_item.location = lib_info.Location or ""
                
                # Check for children
                lib_id = lib_info.id()
                has_children = lib_id in library_children and bool(library_children[lib_id])
                info_item.has_children = has_children
                info_item.is_expanded = lib_id in expanded_libraries
                
                # Add reference children if expanded
                if has_children and info_item.is_expanded:
                    references = library_children[lib_id]
                    
                    # Sort references
                    references.sort(key=lambda ref: (
                        (cls.get_external_reference_id(ref) or "").lower(),
                        (ref.Name or "").lower()
                    ))
                    
                    # Add each reference
                    for ref in references:
                        ref_item = props.libraries.add()
                        ref_item.ifc_definition_id = ref.id()
                        ref_item.is_information = False
                        ref_item.tree_depth = 2
                        ref_item.has_children = False
                        
                        # Set reference properties
                        ref_item.name = ref.Name or ""
                        ref_item.identification = cls.get_external_reference_id(ref) or ""
                        ref_item.description = ref.Description or ""
                        ref_item.location = ref.Location or ""

    @classmethod
    def is_library_information(cls, library: ifcopenshell.entity_instance) -> bool:
        return library.is_a("IfcLibraryInformation")

    @classmethod
    def set_active_library(cls, library: ifcopenshell.entity_instance) -> None:
        props = cls.get_library_props()
        props.active_library_id = library.id()

    @classmethod
    def get_library_information_id(cls, library: ifcopenshell.entity_instance) -> Union[str, None]:
        return library[0]
    @classmethod
    def set_library_information_id(cls, library: ifcopenshell.entity_instance, value: Union[str, None]) -> None:
        library[0] = value

    @classmethod
    def get_external_reference_id(cls, reference: ifcopenshell.entity_instance) -> Union[str, None]:
        return reference[1]

    @classmethod
    def set_external_reference_id(cls, reference: ifcopenshell.entity_instance, value: Union[str, None]) -> None:
        reference[1] = value
