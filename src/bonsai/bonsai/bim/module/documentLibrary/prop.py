# Bonsai - OpenBIM Blender Add-on
# Copyright (C) 2020, 2021 Dion Moult <dion@thinkmoult.com>
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

import bpy
import bonsai.tool as tool
from bonsai.bim.prop import StrProperty, Attribute
from bpy.types import PropertyGroup
from bpy.props import (
    PointerProperty,
    StringProperty,
    EnumProperty,
    BoolProperty,
    IntProperty,
    FloatProperty,
    FloatVectorProperty,
    CollectionProperty,
)
from bonsai.bim.module.documentLibrary.data import DocumentLibraryData
from typing import TYPE_CHECKING, Union


def update_library_name(self: "Library", context: bpy.types.Context) -> None:
    if not self.ifc_definition_id:
        return
    tool.Ifc.get().by_id(self.ifc_definition_id).Name = self.name


def update_library_identification(self: "Library", context: bpy.types.Context) -> None:
    if not self.ifc_definition_id:
        return
    library = tool.Ifc.get().by_id(self.ifc_definition_id)
    if library.is_a("IfcLibraryInformation"):
        tool.DocumentLibrary.set_library_information_id(library, self.identification)
    else:
        tool.DocumentLibrary.set_external_reference_id(library, self.identification)


class Library(PropertyGroup):
    name: StringProperty(name="Name")
    identification: StringProperty(name="Identification")
    description: StringProperty(name="Description")
    is_information: BoolProperty(name="Is Information")
    ifc_definition_id: IntProperty(name="IFC Definition ID")
    location: StringProperty(name="Location", default="")
    tree_depth: IntProperty(name="Tree Depth", default=0)
    has_children: BoolProperty(name="Has Children", default=False)
    is_expanded: BoolProperty(name="Is Expanded", default=False)
    
    if TYPE_CHECKING:
        name: str
        identification: str
        description: str 
        is_information: bool
        ifc_definition_id: int
        location: str
        tree_depth: int
        has_children: bool
        is_expanded: bool


class ExpandedLibraries(PropertyGroup):
    json_string: StringProperty(name="JSON String", default="[]")
    
    if TYPE_CHECKING:
        json_string: str


class LibraryObject(PropertyGroup):
    name: StringProperty(name="Name")
    ifc_definition_id: IntProperty(name="IFC Definition ID")
    
    if TYPE_CHECKING:
        name: str
        ifc_definition_id: int


class AssignedLibrary(PropertyGroup):
    name: StringProperty(name="Name")
    identification: StringProperty(name="Identification")
    description: StringProperty(name="Description", default="")
    is_information: BoolProperty(name="Is Information")
    ifc_definition_id: IntProperty(name="IFC Definition ID")
    location: StringProperty(name="Location", default="")
    
    if TYPE_CHECKING:
        name: str
        identification: str
        is_information: bool
        ifc_definition_id: int
        location: str


def update_active_library(self, context):
    if self.libraries and self.active_library_index < len(self.libraries):
        library = self.libraries[self.active_library_index]
        if library.ifc_definition_id:
            DocumentLibraryData.load_library_objects_into_props(library.ifc_definition_id)


class BIMDocumentLibraryProperties(PropertyGroup):
    library_attributes: CollectionProperty(name="Library Attributes", type=Attribute)
    active_library_id: IntProperty(name="Active Library Id")
    libraries: CollectionProperty(name="Libraries", type=Library)
    active_library_index: IntProperty(name="Active Library Index", update=update_active_library)
    is_editing: BoolProperty(name="Is Editing", default=False)
    is_library_editing: BoolProperty(name="Is Library Editing", default=False)
    is_object_editing: BoolProperty(name="Is Object Editing", default=False)
    library_objects: CollectionProperty(name="Library Objects", type=LibraryObject)
    active_library_object_index: IntProperty(name="Active Library Object Index")
    assigned_libraries: CollectionProperty(name="Assigned Libraries", type=AssignedLibrary)
    active_assigned_library_index: IntProperty(name="Active Assigned Library Index")

    if TYPE_CHECKING:
        library_attributes: bpy.types.bpy_prop_collection_idprop[Attribute]
        active_library_id: int
        libraries: bpy.types.bpy_prop_collection_idprop[Library]
        active_library_index: int
        is_editing: bool
        is_library_editing: bool
        is_object_editing: bool
        library_objects: bpy.types.bpy_prop_collection_idprop[LibraryObject]
        active_library_object_index: int
        assigned_libraries: bpy.types.bpy_prop_collection_idprop[AssignedLibrary]
        active_assigned_library_index: int

    @property
    def active_library(self) -> Union[Library, None]:
        return tool.Blender.get_active_uilist_element(self.libraries, self.active_library_index)
