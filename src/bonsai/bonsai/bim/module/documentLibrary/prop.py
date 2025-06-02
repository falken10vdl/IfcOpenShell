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
from typing import TYPE_CHECKING, Union


def update_document_library_name(self: "DocumentLibrary", context: bpy.types.Context) -> None:
    if not self.ifc_definition_id:
        return
    tool.Ifc.get().by_id(self.ifc_definition_id).Name = self.name


def update_document_library_identification(self: "DocumentLibrary", context: bpy.types.Context) -> None:
    if not self.ifc_definition_id:
        return
    document_library = tool.Ifc.get().by_id(self.ifc_definition_id)
    if document_library.is_a("IfcLibraryInformation"):
        tool.DocumentLibrary.set_library_information_id(document_library, self.identification)
    else:
        tool.DocumentLibrary.set_library_reference_id(document_library, self.identification)


class DocumentLibrary(PropertyGroup):
    name: StringProperty(name="Name", update=update_document_library_name)
    identification: StringProperty(name="Identification", update=update_document_library_identification)
    is_information: BoolProperty(
        name="Is Information",
        description="Whether element is IfcLibraryInformation, otherwise it's IfcLibraryReference.",
    )
    ifc_definition_id: IntProperty(name="IFC Definition ID")

    if TYPE_CHECKING:
        identification: str
        is_information: bool
        ifc_definition_id: int


class DocumentLibraryReferencedObject(PropertyGroup):
    name: StringProperty(name="Name")
    ifc_definition_id: IntProperty(name="IFC Definition ID")
    is_selected: BoolProperty(name="Is Selected", default=False)


class BIMDocumentLibraryProperties(PropertyGroup):
    document_library_attributes: CollectionProperty(name="Document Library Attributes", type=Attribute)
    active_document_library_id: IntProperty(name="Active Document Library Id")
    document_libraries: CollectionProperty(name="Document Libraries", type=DocumentLibrary)
    document_library_breadcrumbs: CollectionProperty(name="Document Library Breadcrumbs", type=StrProperty)
    active_document_library_index: IntProperty(name="Active Document Library Index")
    is_editing: BoolProperty(name="Is Editing", default=False)
    document_library_referenced_objects: CollectionProperty(name="Document Library Referenced Objects", type=DocumentLibraryReferencedObject)
    active_document_library_referenced_object_index: IntProperty(name="Active Document Library Referenced Object Index")

    if TYPE_CHECKING:
        document_library_attributes: bpy.types.bpy_prop_collection_idprop[Attribute]
        active_document_library_id: int
        document_libraries: bpy.types.bpy_prop_collection_idprop[DocumentLibrary]
        document_library_breadcrumbs: bpy.types.bpy_prop_collection_idprop[StrProperty]
        active_document_library_index: int
        is_editing: bool

    @property
    def active_document_library(self) -> Union[DocumentLibrary, None]:
        return tool.Blender.get_active_uilist_element(self.document_libraries, self.active_document_library_index)
