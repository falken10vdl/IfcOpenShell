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
    def get_document_library_props(cls) -> BIMDocumentLibraryProperties:
        return bpy.context.scene.BIMDocumentLibraryProperties

    @classmethod
    def add_breadcrumb(cls, document_library: ifcopenshell.entity_instance) -> None:
        props = cls.get_document_library_props()
        new = props.document_library_breadcrumbs.add()
        new.name = str(document_library.id()) 

    @classmethod
    def clear_breadcrumbs(cls) -> None:
        props = cls.get_document_library_props()
        props.document_library_breadcrumbs.clear()

    @classmethod
    def clear_document_library_tree(cls) -> None:
        props = cls.get_document_library_props()
        props.document_libraries.clear()

    @classmethod
    def disable_editing_document_library(cls) -> None:
        props = cls.get_document_library_props()
        props.active_document_library_id = 0

    @classmethod
    def disable_document_library_editing_ui(cls) -> None:
        props = cls.get_document_library_props()
        props.is_editing = False

    @classmethod
    def enable_document_library_editing_ui(cls) -> None:
        props = cls.get_document_library_props()
        props.is_editing = True

    @classmethod
    def export_document_library_attributes(cls) -> dict[str, Any]:
        props = cls.get_document_library_props()
        return bonsai.bim.helper.export_attributes(props.document_library_attributes)

    @classmethod
    def get_active_breadcrumb(cls) -> Union[ifcopenshell.entity_instance, None]:
        props = cls.get_document_library_props()
        if len(props.document_library_breadcrumbs):
            return tool.Ifc.get().by_id(int(props.document_library_breadcrumbs[-1].name))

    @classmethod
    def import_document_library_attributes(cls, document_library: ifcopenshell.entity_instance) -> None:
        props = cls.get_document_library_props()
        props.document_library_attributes.clear()
        
        def callback(attr_name: str, attr_value, data: dict[str, Any]) -> Union[bool, None]:
            if attr_name == "Name":
                return None
            return None
        
        bonsai.bim.helper.import_attributes2(document_library, props.document_library_attributes, callback=callback)
        
        name_found = False
        for attr in props.document_library_attributes:
            if attr.name == "Name":
                name_found = True
                break
        
        if not name_found:
            name_prop = props.document_library_attributes.add()
            name_prop.name = "Name"
            name_prop.data_type = "string"
            if document_library.is_a("IfcLibraryInformation"):
                name_prop.string_value = document_library.Name or "UnnamedInformation"
            else:
                name_prop.string_value = document_library.Name or "UnnamedReference"

    @classmethod
    def import_project_document_libraries(cls) -> None:
        props = cls.get_document_library_props()
        props.document_libraries.clear()
        
        ifc_file = tool.Ifc.get()
        if not ifc_file:
            return
        
        all_libraries = ifc_file.by_type("IfcLibraryInformation")
        
        child_libraries = set()
        
        project_libraries = set()
        if ifc_file.by_type("IfcProject"):
            project = ifc_file.by_type("IfcProject")[0]
            for rel in getattr(project, "HasAssociations", []) or []:
                if rel.is_a("IfcRelAssociatesLibrary") and rel.RelatingLibrary.is_a("IfcLibraryInformation"):
                    project_libraries.add(rel.RelatingLibrary.id())
        
        for rel in ifc_file.by_type("IfcRelAssociatesLibrary"):
            if rel.RelatingLibrary.is_a("IfcLibraryInformation"):
                child_libraries.add(rel.RelatingLibrary.id())
        
        for element in all_libraries:
            if element.id() in project_libraries or element.id() not in child_libraries:
                new = props.document_libraries.add()
                new.ifc_definition_id = element.id()
                new["name"] = element.Name or "UnnamedInformation"
                new.is_information = True

    @classmethod
    def import_references(cls, document_library: ifcopenshell.entity_instance) -> None:
        props = cls.get_document_library_props()
        references = cls.get_library_references(document_library)
        
        for element in references:
            if element.is_a("IfcLibraryReference"):
                new = props.document_libraries.add()
                new.ifc_definition_id = element.id()
                # Use Name directly instead of Description + Location
                new["name"] = element.Name or "UnnamedReference"
                new["identification"] = element.Identification or ""
                new.is_information = False

    @classmethod
    def import_sublibraries(cls, document_library: ifcopenshell.entity_instance) -> None:
        """Import only true sublibraries, not references"""
        props = cls.get_document_library_props()
        
        # Find all library information entities that relate to this one
        ifc_file = tool.Ifc.get()
        for rel in ifc_file.by_type("IfcRelAssociatesLibrary"):
            # If this library is in the RelatedObjects, the RelatingLibrary is a sublibrary
            if document_library in rel.RelatedObjects and rel.RelatingLibrary.is_a("IfcLibraryInformation"):
                element = rel.RelatingLibrary
                new = props.document_libraries.add()
                new.ifc_definition_id = element.id()
                new["name"] = element.Name or "UnnamedInformation"
                new.is_information = True

    @classmethod
    def is_library_information(cls, document_library: ifcopenshell.entity_instance) -> bool:
        return document_library.is_a("IfcLibraryInformation")

    @classmethod
    def remove_latest_breadcrumb(cls) -> None:
        props = cls.get_document_library_props()
        if len(props.document_library_breadcrumbs) > 0:
            # Remove the last breadcrumb
            props.document_library_breadcrumbs.remove(len(props.document_library_breadcrumbs) - 1)
            # Debug
            print(f"Removed breadcrumb, current count: {len(props.document_library_breadcrumbs)}")
            if len(props.document_library_breadcrumbs) > 0:
                print(f"New active breadcrumb: {props.document_library_breadcrumbs[-1].name}")

    @classmethod
    def set_active_document_library(cls, document_library: ifcopenshell.entity_instance) -> None:
        props = cls.get_document_library_props()
        props.active_document_library_id = document_library.id()
    
    @classmethod
    def get_library_information_id(cls, document_library: ifcopenshell.entity_instance) -> Union[str, None]:
        """Get IfcLibraryInformation.Identification, compatible with IFC2X3."""
        return document_library[0]

    @classmethod
    def set_library_information_id(cls, document_library: ifcopenshell.entity_instance, value: Union[str, None]) -> None:
        """Set IfcLibraryInformation.Identification, compatible with IFC2X3."""
        document_library[0] = value

    @classmethod
    def get_external_library_reference_id(cls, reference: ifcopenshell.entity_instance) -> Union[str, None]:
        """Get IfcLibraryReference.Identification, compatible with IFC2X3."""
        return reference[1]

    @classmethod
    def set_external_library_reference_id(cls, reference: ifcopenshell.entity_instance, value: Union[str, None]) -> None:
        """Set IfcLibraryReference.Identification, compatible with IFC2X3."""
        reference[1] = value

    @classmethod
    def get_library_references(
        cls, document_library: ifcopenshell.entity_instance
    ) -> tuple[ifcopenshell.entity_instance, ...]:
        """Get references from a library entity, compatible with IFC2X3."""
        if document_library.file.schema == "IFC2X3":
            return document_library.LibraryReferences or ()
        return document_library.HasLibraryReferences

    @classmethod
    def load_referenceable_objects(cls, document_library: ifcopenshell.entity_instance) -> None:
        """Load objects that are referenced by this document library."""
        props = cls.get_document_library_props()
        props.document_library_referenced_objects.clear()

        # Get objects referenced by this library using the utility function
        referenced_products = ifcopenshell.util.element.get_referenced_elements(document_library)

        # Add them to the list
        for product in referenced_products:
            # We only care about physical objects (IfcProducts)
            if not product.is_a("IfcProduct"):
                continue

            obj = tool.Ifc.get_object(product)
            if obj:
                item = props.document_library_referenced_objects.add()
                item.name = obj.name or f"#{product.id()}"
                item.ifc_definition_id = product.id()