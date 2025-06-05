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
            "document_objects": cls.document_objects(),
        }
        cls.is_loaded = True

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

    @classmethod
    def document_objects(cls):
        """Returns a dictionary mapping document IDs to their referenced objects"""
        document_objects = {}
        file = tool.Ifc.get()
        
        for rel in file.by_type("IfcRelAssociatesDocument"):
            document_id = rel.RelatingDocument.id()
            if document_id not in document_objects:
                document_objects[document_id] = []
                
            for related_object in rel.RelatedObjects:
                element = related_object
                obj = tool.Ifc.get_object(element)
                if obj:
                    document_objects[document_id].append({
                        "id": element.id(), 
                        "name": obj.name,
                        "obj": obj
                    })
                    
        return document_objects

    @classmethod
    def load_document_objects_into_props(cls, document_id):
        """Loads objects related to a document into property collection"""
        props = tool.Document.get_document_props()
        props.document_objects.clear()
        
        if "document_objects" not in cls.data or document_id not in cls.data["document_objects"]:
            return
            
        # Sort the objects by name before adding them to the collection
        sorted_objects = sorted(cls.data["document_objects"][document_id], key=lambda x: x["name"].lower())
        
        for obj_data in sorted_objects:
            item = props.document_objects.add()
            item.name = obj_data["name"]
    

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

                name = rel.RelatingDocument.Name

                if tool.Ifc.get_schema() == "IFC2X3":
                    if not name and rel.RelatingDocument.ReferenceToDocument:
                        name = rel.RelatingDocument.ReferenceToDocument[0].Name

                    identification = rel.RelatingDocument.ItemReference
                    if not identification and rel.RelatingDocument.ReferenceToDocument:
                        identification = rel.RelatingDocument.ReferenceToDocument[0].DocumentId

                    location = rel.RelatingDocument.Location
                else:
                    if not name and rel.RelatingDocument.ReferencedDocument:
                        name = rel.RelatingDocument.ReferencedDocument.Name

                    identification = rel.RelatingDocument.Identification
                    if not identification and rel.RelatingDocument.ReferencedDocument:
                        identification = rel.RelatingDocument.ReferencedDocument.Identification

                    location = rel.RelatingDocument.Location
                    if location is None and rel.RelatingDocument.ReferencedDocument:
                        location = rel.RelatingDocument.ReferencedDocument.Location

                if location:
                    if not "://" in location:
                        if not os.path.isabs(location):
                            location = os.path.abspath(os.path.join(os.path.dirname(tool.Ifc.get_path()), location))
                        location = "file://" + location

                results.append(
                    {
                        "id": rel.RelatingDocument.id(),
                        "identification": identification,
                        "name": name,
                        "location": location,
                    }
                )
        return results
