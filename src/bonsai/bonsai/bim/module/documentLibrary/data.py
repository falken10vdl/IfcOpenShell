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

                library = rel.RelatingLibrary
                name = library.Name
                identification = getattr(library, "Identification", None) or ""
                location = getattr(library, "Location", None)
                
                # Add flag to identify the type and get description for references
                is_reference = library.is_a("IfcLibraryReference")
                description = None
                
                if is_reference:
                    # Get description for references
                    if hasattr(library, "Description") and library.Description:
                        description = library.Description
                    
                    # Handle references to IfcLibraryInformation
                    if hasattr(library, "ReferencedLibrary") and library.ReferencedLibrary:
                        ref_lib = library.ReferencedLibrary
                        # Use referenced library name if reference name is empty
                        if not name:
                            name = ref_lib.Name
                        # Use referenced library identification if reference identification is empty
                        if not identification:
                            identification = getattr(ref_lib, "Identification", None) or ""
                        # Use referenced library location if reference location is empty
                        if not location and hasattr(ref_lib, "Location"):
                            location = ref_lib.Location
                        # Use referenced library description if we don't have one
                        if not description and hasattr(ref_lib, "Description") and ref_lib.Description:
                            description = ref_lib.Description
                
                # For IFC2X3 compatibility
                if tool.Ifc.get_schema() == "IFC2X3" and hasattr(library, "LibraryReference") and library.LibraryReference:
                    lib_ref = library.LibraryReference
                    if not name:
                        name = lib_ref.Name
                    if not identification:
                        identification = lib_ref.Identification
                    if not location and hasattr(lib_ref, "Location"):
                        location = lib_ref.Location
                    if not description and hasattr(lib_ref, "Description") and lib_ref.Description:
                        description = lib_ref.Description

                # Handle file paths for location
                if location:
                    if not "://" in location:
                        if not os.path.isabs(location):
                            location = os.path.abspath(os.path.join(os.path.dirname(tool.Ifc.get_path()), location))
                        location = "file://" + location

                results.append(
                    {
                        "id": library.id(),
                        "identification": identification,
                        "name": name or "Unnamed",
                        "description": description,  # Add description field
                        "location": location,
                        "is_information": library.is_a("IfcLibraryInformation"),
                        "is_reference": is_reference  # Add flag to identify references
                    }
                )
        return results
