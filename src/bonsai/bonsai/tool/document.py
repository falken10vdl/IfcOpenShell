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
    from bonsai.bim.module.document.prop import BIMDocumentProperties


class Document(bonsai.core.tool.Document):
    @classmethod
    def get_document_props(cls) -> BIMDocumentProperties:
        return bpy.context.scene.BIMDocumentProperties


    @classmethod
    def clear_document_tree(cls) -> None:
        props = cls.get_document_props()
        props.documents.clear()

    @classmethod
    def disable_editing_document(cls) -> None:
        props = cls.get_document_props()
        props.active_document_id = 0

    @classmethod
    def disable_editing_ui(cls) -> None:
        props = cls.get_document_props()
        props.is_editing = False

    @classmethod
    def enable_editing_ui(cls) -> None:
        props = cls.get_document_props()
        props.is_editing = True

    @classmethod
    def export_document_attributes(cls) -> dict[str, Any]:
        props = cls.get_document_props()
        return bonsai.bim.helper.export_attributes(props.document_attributes)

    @classmethod
    def import_document_attributes(cls, document: ifcopenshell.entity_instance) -> None:
        props = cls.get_document_props()
        props.document_attributes.clear()

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
            # for IfcDocumentReference with ReferencedDocument.
            return False

        import_callback = callback if document.is_a("IfcDocumentReference") else None
        bonsai.bim.helper.import_attributes2(document, props.document_attributes, callback=import_callback)

    @classmethod
    def import_project_documents(cls) -> None:
        props = cls.get_document_props()
        props.documents.clear()
        file = tool.Ifc.get()
        
        # Get expanded documents state
        import json
        expanded_documents = []
        try:
            expanded_documents = json.loads(bpy.context.scene.ExpandedDocuments.json_string)
        except (AttributeError, json.JSONDecodeError):
            pass
                
        project = file.by_type("IfcProject")[0] if file.by_type("IfcProject") else None
        if not project:
            return
                
        # Build document hierarchy mapping
        document_children = {}  # Maps document ID to its children
        
        # First, identify parent-child relationships using IfcDocumentInformationRelationship
        for rel in file.by_type("IfcDocumentInformationRelationship"):
            parent_id = rel.RelatingDocument.id()
            if parent_id not in document_children:
                document_children[parent_id] = []
            
            # Add all related documents as children
            for child in rel.RelatedDocuments:
                document_children[parent_id].append(child)
        
        # Add document references to their parent information documents
        is_ifc2x3 = file.schema == "IFC2X3"
        
        # For IFC2X3, use ReferenceToDocument inverse relationship
        if is_ifc2x3:
            for ref in file.by_type("IfcDocumentReference"):
                if ref.ReferenceToDocument:
                    parent = ref.ReferenceToDocument[0]
                    parent_id = parent.id()
                    if parent_id not in document_children:
                        document_children[parent_id] = []
                    document_children[parent_id].append(ref)
        else:
            # For IFC4+, use ReferencedDocument direct attribute
            for ref in file.by_type("IfcDocumentReference"):
                if hasattr(ref, "ReferencedDocument") and ref.ReferencedDocument:
                    parent = ref.ReferencedDocument
                    parent_id = parent.id()
                    if parent_id not in document_children:
                        document_children[parent_id] = []
                    document_children[parent_id].append(ref)
        
        # Collect root documents (those directly associated with the project)
        root_documents = []
        for rel in project.HasAssociations or []:
            if rel.is_a("IfcRelAssociatesDocument") and rel.RelatingDocument.is_a("IfcDocumentInformation"):
                # Only add as root if not a child in any relationship
                is_child = False
                for children in document_children.values():
                    if rel.RelatingDocument in children:
                        is_child = True
                        break
                            
                if not is_child:
                    root_documents.append(rel.RelatingDocument)
        
        # Create a virtual root element for all documents
        root = props.documents.add()
        root.ifc_definition_id = -1  # Special ID to identify the root
        root.is_information = True
        root.name = f"Project Documents ({project.Name or 'Unnamed Project'})"
        root.identification = ""
        root.location = ""
        root.tree_depth = 0
        root.has_children = bool(root_documents)  # Only show expand if there are documents
        
        # Use special ID (negative project.id()) to identify the root in expanded documents
        root_id = -project.id()  # Use negative project ID as the unique identifier
        
        # Default the root to be expanded if not explicitly collapsed
        root.is_expanded = root_id not in expanded_documents
        
        # If root is expanded, add all documents
        if root.is_expanded:
            # Sort root documents by identification then name
            root_documents.sort(key=lambda doc: (
                (cls.get_document_information_id(doc) or "").lower(),
                (doc.Name or "").lower()
            ))
            
            # Process each root document
            for doc in root_documents:
                cls._process_document(doc, props, document_children, expanded_documents, 1)  # Start at depth 1

    @classmethod
    def _process_document(cls, document, props, document_children, expanded_documents, depth):
        """Process a document and its children recursively"""
        # Add this document
        new = props.documents.add()
        new.ifc_definition_id = document.id()
        new.is_information = document.is_a("IfcDocumentInformation")
        new.tree_depth = depth
        
        # Get the file from the document instance
        file = document.file  # Use document's file instead of cls.file
        
        # Set document properties
        if new.is_information:
            new.name = document.Name or "Unnamed"
            new.identification = cls.get_document_information_id(document) or ""
            new.location = document.Location or ""
        else:
            new.name = document.Name or ""
            new.identification = cls.get_external_reference_id(document) or ""
            new.description = document.Description or ""
            new.location = document.Location or ""
            
            # Add additional reference data from referenced document if applicable
            if not new.is_information:
                if file.schema == "IFC2X3":  # Use file from document
                    if document.ReferenceToDocument:
                        doc_info = document.ReferenceToDocument[0]
                        if not new.name:
                            new.name = doc_info.Name or ""
                        new.location = new.location or ""
                else:
                    if hasattr(document, "ReferencedDocument") and document.ReferencedDocument:
                        doc_info = document.ReferencedDocument
                        if not new.name:
                            new.name = doc_info.Name or ""
                        new.location = new.location or ""
        
        # Check if this document has children
        doc_id = document.id()
        has_children = doc_id in document_children and bool(document_children[doc_id])
        new.has_children = has_children
        new.is_expanded = doc_id in expanded_documents
        
        # Process children if expanded
        if has_children and new.is_expanded:
            children = document_children[doc_id]
            
            # Sort children
            children.sort(key=lambda doc: (
                doc.is_a("IfcDocumentInformation"),  # Sort information docs before references
                (cls.get_document_information_id(doc) if doc.is_a("IfcDocumentInformation") 
                else cls.get_external_reference_id(doc) or "").lower(),
                (doc.Name or "").lower()
            ), reverse=True)  # Information docs first
            
            # Process each child
            for child in children:
                cls._process_document(child, props, document_children, expanded_documents, depth + 1)

    @classmethod
    def is_document_information(cls, document: ifcopenshell.entity_instance) -> bool:
        return document.is_a("IfcDocumentInformation")



    @classmethod
    def set_active_document(cls, document: ifcopenshell.entity_instance) -> None:
        props = cls.get_document_props()
        props.active_document_id = document.id()

    @classmethod
    def get_document_information_id(cls, document: ifcopenshell.entity_instance) -> Union[str, None]:
        """Get IfcDocumentInformation.DocumentId/Identification, compatible with IFC2X3."""
        return document[0]

    @classmethod
    def set_document_information_id(cls, document: ifcopenshell.entity_instance, value: Union[str, None]) -> None:
        """Set IfcDocumentInformation.DocumentId/Identification, compatible with IFC2X3."""
        document[0] = value

    @classmethod
    def get_external_reference_id(cls, reference: ifcopenshell.entity_instance) -> Union[str, None]:
        """Get IfcExternalReference.ItemReference/Identification, compatible with IFC2X3."""
        return reference[1]

    @classmethod
    def set_external_reference_id(cls, reference: ifcopenshell.entity_instance, value: Union[str, None]) -> None:
        """Set IfcExternalReference.ItemReference/Identification, compatible with IFC2X3."""
        reference[1] = value

    @classmethod
    def get_document_references(
        cls, document: ifcopenshell.entity_instance
    ) -> tuple[ifcopenshell.entity_instance, ...]:
        """Get IfcDocumentReference.ReferencedDocuments, compatible with IFC2X3."""
        if document.file.schema == "IFC2X3":
            return document.DocumentReferences or ()
        return document.HasDocumentReferences
