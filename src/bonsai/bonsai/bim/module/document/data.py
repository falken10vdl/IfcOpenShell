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

        cls.data["document_information_relationship_objects"] = {}
        for rel in tool.Ifc.get().by_type("IfcDocumentInformationRelationship"):
            # The relating document is the "parent" document
            relating_doc = rel.RelatingDocument
            relating_doc_id = relating_doc.id()
            relating_doc_name = relating_doc.Name or f"#{relating_doc_id}"
            
            # For each related document, add the relating document to its list
            for doc in rel.RelatedDocuments:
                doc_id = doc.id()
                if doc_id not in cls.data["document_information_relationship_objects"]:
                    cls.data["document_information_relationship_objects"][doc_id] = []
                
                # Add the relating document's name to this document's list
                cls.data["document_information_relationship_objects"][doc_id].append(
                    f"↑ {relating_doc_name}"
                )

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
                if not rel.RelatingDocument.is_a("IfcDocumentReference"):
                    continue

                document = rel.RelatingDocument
                name = document.Name
                description = None

                # Try to get description directly from DocumentReference
                if hasattr(document, "Description") and document.Description:
                    description = document.Description

                if tool.Ifc.get_schema() == "IFC2X3":
                    if not name and document.ReferenceToDocument:
                        name = document.ReferenceToDocument[0].Name
                    
                    # Try to get description from referenced document in IFC2X3
                    if not description and document.ReferenceToDocument:
                        if hasattr(document.ReferenceToDocument[0], "Description"):
                            description = document.ReferenceToDocument[0].Description

                    identification = document.ItemReference
                    if not identification and document.ReferenceToDocument:
                        identification = document.ReferenceToDocument[0].DocumentId

                    location = document.Location
                else:
                    if not name and document.ReferencedDocument:
                        name = document.ReferencedDocument.Name
                    
                    # Try to get description from referenced document in IFC4+
                    if not description and document.ReferencedDocument:
                        if hasattr(document.ReferencedDocument, "Description"):
                            description = document.ReferencedDocument.Description

                    identification = document.Identification
                    if not identification and document.ReferencedDocument:
                        identification = document.ReferencedDocument.Identification

                    location = document.Location
                    if location is None and document.ReferencedDocument:
                        location = document.ReferencedDocument.Location

                # If we still don't have a description, use name as fallback
                description = description or name

                if location:
                    if not "://" in location:
                        if not os.path.isabs(location):
                            location = os.path.abspath(os.path.join(os.path.dirname(tool.Ifc.get_path()), location))
                        location = "file://" + location

                results.append(
                    {
                        "id": document.id(),
                        "identification": identification,
                        "name": name,
                        "description": description,  # Add the description field
                        "location": location,
                    }
                )
        return results
