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
    DocumentLibraryData.is_loaded = False
    ObjectDocumentLibraryData.is_loaded = False


class DocumentLibraryData:
    data = {}
    is_loaded = False

    @classmethod
    def load(cls):
        cls.data = {
            "total_information": cls.total_information(),
            "parent_document_library": cls.parent_document_library(),
        }
        cls.is_loaded = True

        cls.data["document_library_references"] = {}
        for rel in tool.Ifc.get().by_type("IfcRelAssociatesLibrary"):
            lib_id = rel.RelatingLibrary.id()
            if lib_id not in cls.data["document_library_references"]:
                cls.data["document_library_references"][lib_id] = []

            for obj in rel.RelatedObjects:
                name = obj.Name or f"#{obj.id()}"
                cls.data["document_library_references"][lib_id].append(name)

    @classmethod
    def total_information(cls):
        ifc_file = tool.Ifc.get()
        if not ifc_file:
            return 0
            
        all_libraries = ifc_file.by_type("IfcLibraryInformation")
        
        child_libraries = set()
        for rel in ifc_file.by_type("IfcRelAssociatesLibrary"):
            if rel.RelatingLibrary.is_a("IfcLibraryInformation"):
                for obj in rel.RelatedObjects:
                    if obj.is_a("IfcLibraryInformation"):
                        child_libraries.add(obj.id())
        
        return len([lib for lib in all_libraries if lib.id() not in child_libraries])

    @classmethod
    def parent_document_library(cls):
        props = tool.DocumentLibrary.get_document_library_props()
        if len(props.document_library_breadcrumbs):
            parent_id = int(props.document_library_breadcrumbs[-1].name)
            parent = tool.Ifc.get().by_id(parent_id)
            return str(parent.Identification if hasattr(parent, "Identification") else "")
        return ""


class ObjectDocumentLibraryData:
    data = {}
    is_loaded = False

    @classmethod
    def load(cls):
        cls.data = {
            "document_libraries": cls.document_libraries(),
        }
        cls.is_loaded = True

    @classmethod
    def document_libraries(cls):
        results = []
        element = tool.Ifc.get_entity(bpy.context.active_object)
        if not element:
            return results
        for rel in getattr(element, "HasAssociations", []):
            if rel.is_a("IfcRelAssociatesLibrary"):
                # Check if RelatingLibrary is one of the acceptable types
                if not (rel.RelatingLibrary.is_a("IfcLibraryReference") or rel.RelatingLibrary.is_a("IfcLibraryInformation")):
                    continue

                name = rel.RelatingLibrary.Name
                identification = getattr(rel.RelatingLibrary, "Identification", None) or ""
                location = getattr(rel.RelatingLibrary, "Location", None)
                
                # Handle references to external sources
                if hasattr(rel.RelatingLibrary, "LibraryReference") and rel.RelatingLibrary.LibraryReference:
                    if not name:
                        name = rel.RelatingLibrary.LibraryReference.Name
                    if not identification:
                        identification = rel.RelatingLibrary.LibraryReference.Identification
                    if not location and hasattr(rel.RelatingLibrary.LibraryReference, "Location"):
                        location = rel.RelatingLibrary.LibraryReference.Location

                if location:
                    if not "://" in location:
                        if not os.path.isabs(location):
                            location = os.path.abspath(os.path.join(os.path.dirname(tool.Ifc.get_path()), location))
                        location = "file://" + location

                results.append(
                    {
                        "id": rel.RelatingLibrary.id(),
                        "identification": identification,
                        "name": name or "Unnamed",
                        "location": location,
                        "is_information": rel.RelatingLibrary.is_a("IfcLibraryInformation"),
                    }
                )
        return results
