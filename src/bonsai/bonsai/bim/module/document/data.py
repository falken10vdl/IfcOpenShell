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

import os
import bpy
import ifcopenshell
import ifcopenshell.util.schema
import bonsai.tool as tool


def refresh():
    DocumentData.is_loaded = False
    ObjectDocumentData.is_loaded = False


class DocumentData:
    data = {}
    is_loaded = False

    @classmethod
    def load(cls):
        cls.data = {
            "total_information": cls.total_information(),
            "parent_document": cls.parent_document(),
        }
        cls.is_loaded = True

        cls.data["document_references"] = {}
        for rel in tool.Ifc.get().by_type("IfcRelAssociatesDocument"):
            doc_id = rel.RelatingDocument.id()
            if doc_id not in cls.data["document_references"]:
                cls.data["document_references"][doc_id] = []

            for obj in rel.RelatedObjects:
                name = obj.Name or f"#{obj.id()}"
                cls.data["document_references"][doc_id].append(name)

    @classmethod
    def total_information(cls):
        return len(
            [
                rel
                for rel in tool.Ifc.get().by_type("IfcProject")[0].HasAssociations or []
                if rel.is_a("IfcRelAssociatesDocument") and rel.RelatingDocument.is_a("IfcDocumentInformation")
            ]
        )

    @classmethod
    def parent_document(cls):
        props = tool.Document.get_document_props()
        if len(props.breadcrumbs):
            parent = tool.Ifc.get().by_id(int(props.breadcrumbs[-1].name))
            if tool.Ifc.get_schema() == "IFC2X3":
                return str(parent.DocumentId)
            return str(parent.Identification)
        return ""


class ObjectDocumentData:
    data = {}
    is_loaded = False

    @classmethod
    def load(cls):
        cls.data = {
            "documents": cls.documents(),
        }
        cls.is_loaded = True

    @classmethod
    def documents(cls):
        results = []
        element = tool.Ifc.get_entity(bpy.context.active_object)
        if not element:
            return results
            
        for rel in getattr(element, "HasAssociations", []):
            if rel.is_a("IfcRelAssociatesDocument"):
                document = rel.RelatingDocument
                
                # Get common attributes with defaults
                name = document.Name or "Unnamed"
                identification = None
                location = None
                description = getattr(document, "Description", None)
                is_reference = document.is_a("IfcDocumentReference")
                
                # Handle schema and type-specific attribute retrieval
                if is_reference:
                    # Document Reference
                    if tool.Ifc.get_schema() == "IFC2X3":
                        if not name and document.ReferenceToDocument:
                            name = document.ReferenceToDocument[0].Name
                            
                        identification = document.ItemReference
                        if not identification and document.ReferenceToDocument:
                            identification = document.ReferenceToDocument[0].DocumentId
                            
                        location = document.Location
                    else:
                        if not name and document.ReferencedDocument:
                            name = document.ReferencedDocument.Name
                            
                        identification = document.Identification
                        if not identification and document.ReferencedDocument:
                            identification = document.ReferencedDocument.Identification
                            
                        location = document.Location
                        if location is None and document.ReferencedDocument:
                            location = document.ReferencedDocument.Location
                            
                        # Get description from referenced document if not available in reference
                        if not description and document.ReferencedDocument:
                            description = getattr(document.ReferencedDocument, "Description", None)
                else:
                    # Document Information
                    identification = document.Identification if hasattr(document, "Identification") else None
                    location = document.Location if hasattr(document, "Location") else None
                
                # Format location paths
                if location:
                    if not "://" in location:
                        if not os.path.isabs(location):
                            location = os.path.abspath(os.path.join(os.path.dirname(tool.Ifc.get_path()), location))
                        location = "file://" + location
                
                # Add the document to results
                results.append({
                    "id": document.id(),
                    "identification": identification,
                    "name": name,
                    "description": description,
                    "location": location,
                    "is_reference": is_reference
                })
                
        return results