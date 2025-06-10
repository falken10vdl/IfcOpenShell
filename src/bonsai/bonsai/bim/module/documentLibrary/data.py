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
            "total_library_informations": cls.total_library_informations(),
            "total_library_references": cls.total_library_references(),
            "total_referenced_objects": cls.total_referenced_objects(),
            "library_objects": cls.library_objects(),
        }
        cls.is_loaded = True

    @classmethod
    def total_library_informations(cls):
        file = tool.Ifc.get()
        info_count = len(file.by_type("IfcLibraryInformation"))
        return info_count

    @classmethod
    def total_library_references(cls):
        file = tool.Ifc.get()
        ref_count = len(file.by_type("IfcLibraryReference"))
        return ref_count
    
    @classmethod
    def total_referenced_objects(cls):
        file = tool.Ifc.get()
        library_rels = file.by_type("IfcRelAssociatesLibrary")
        referenced_objects = set()
        for rel in library_rels:
            if not rel.RelatingLibrary:
                continue
                
            for related_object in rel.RelatedObjects:
                obj = tool.Ifc.get_object(related_object)
                if obj:
                    referenced_objects.add(related_object.id())
        
        return len(referenced_objects)

    @classmethod
    def library_objects(cls):
        library_objects = {}
        file = tool.Ifc.get()
        
        for rel in file.by_type("IfcRelAssociatesLibrary"):
            if not rel.RelatingLibrary:
                continue
                
            library_id = rel.RelatingLibrary.id()
            if library_id not in library_objects:
                library_objects[library_id] = []
                
            for related_object in rel.RelatedObjects:
                element = related_object
                obj = tool.Ifc.get_object(element)
                if obj:
                    library_objects[library_id].append({
                        "id": element.id(), 
                        "name": obj.name,
                        "obj": obj
                    })
                    
        return library_objects

    @classmethod
    def load_library_objects_into_props(cls, library_id):
        props = tool.DocumentLibrary.get_library_props()
        props.library_objects.clear()
        
        if "library_objects" not in cls.data or library_id not in cls.data["library_objects"]:
            return
            
        sorted_objects = sorted(cls.data["library_objects"][library_id], key=lambda x: x["name"].lower())
        
        for obj_data in sorted_objects:
            item = props.library_objects.add()
            item.name = obj_data["name"]
    

class ObjectDocumentLibraryData:
    data = {}
    is_loaded = False

    @classmethod
    def load(cls):
        cls.data = {
            "libraries": cls.libraries(),
        }
        cls.is_loaded = True

    @classmethod
    def libraries(cls):
        results = []
        element = tool.Ifc.get_entity(bpy.context.active_object)
        if not element:
            return results
            
        for rel in getattr(element, "HasAssociations", []):
            if rel.is_a("IfcRelAssociatesLibrary"):
                # Check if RelatingLibrary is None before accessing it
                if not rel.RelatingLibrary:
                    continue
                    
                is_information = rel.RelatingLibrary.is_a("IfcLibraryInformation")
                is_reference = rel.RelatingLibrary.is_a("IfcLibraryReference")
                
                if not (is_information or is_reference):
                    continue
                    
                # Get name and other attributes safely
                name = getattr(rel.RelatingLibrary, "Name", "") or ""
                description = getattr(rel.RelatingLibrary, "Description", "") or ""
                location = getattr(rel.RelatingLibrary, "Location", "") or ""
                
                # Create result dictionary based on entity type
                result = {
                    "id": rel.RelatingLibrary.id(),
                    "name": name,
                    "description": description,
                    "location": location,
                    "is_information": is_information,
                }
                
                # Only add identification for references, not for information entities
                if is_reference:
                    # For IfcLibraryReference, try ItemReference or similar attributes
                    identification = ""
                    if hasattr(rel.RelatingLibrary, "ItemReference"):
                        identification = rel.RelatingLibrary.ItemReference
                    elif hasattr(rel.RelatingLibrary, "Identification"):
                        identification = rel.RelatingLibrary.Identification
                    
                    result["identification"] = identification
                    
                results.append(result)
                    
        return results
