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
from typing import TYPE_CHECKING, Union


def update_document_name(self: "Document", context: bpy.types.Context) -> None:
    if not self.ifc_definition_id:
        return
    tool.Ifc.get().by_id(self.ifc_definition_id).Name = self.name


def update_document_identification(self: "Document", context: bpy.types.Context) -> None:
    if not self.ifc_definition_id:
        return
    document = tool.Ifc.get().by_id(self.ifc_definition_id)
    if document.is_a("IfcDocumentInformation"):
        tool.Document.set_document_information_id(document, self.identification)
    else:
        tool.Document.set_external_reference_id(document, self.identification)


class Document(PropertyGroup):
    name: StringProperty(name="Name", update=update_document_name)
    identification: StringProperty(name="Identification", update=update_document_identification)
    is_information: BoolProperty(
        name="Is Information",
        description="Whether element is IfcDocumentInformation, otherwise it's IfcDocumentReference.",
    )
    ifc_definition_id: IntProperty(name="IFC Definition ID")

    if TYPE_CHECKING:
        identification: str
        is_information: bool
        ifc_definition_id: int


class DocumentReferencedObject(PropertyGroup):
    name: StringProperty(name="Name")
    ifc_definition_id: IntProperty(name="IFC Definition ID")
    is_selected: BoolProperty(name="Is Selected", default=False)


def update_active_document(self: "BIMDocumentProperties", context: bpy.types.Context) -> None:
    tool.Document.update_active_document_referenced_objects()

class BIMDocumentProperties(PropertyGroup):
    document_attributes: CollectionProperty(name="Document Attributes", type=Attribute)
    active_document_id: IntProperty(name="Active Document Id", update=update_active_document, default=0)
    documents: CollectionProperty(name="Documents", type=Document)
    breadcrumbs: CollectionProperty(name="Breadcrumbs", type=StrProperty)
    is_editing: BoolProperty(name="Is Editing", default=False)
    is_editing_document: BoolProperty(name="Is Editing Document", default=False)
    document_referenced_objects: CollectionProperty(name="Document Referenced Objects", type=DocumentReferencedObject)
    active_referenced_object_id: IntProperty(name="Active Referenced Object Id", default=0)

    if TYPE_CHECKING:
        document_attributes: bpy.types.bpy_prop_collection_idprop[Attribute]
        active_document_id: int
        documents: bpy.types.bpy_prop_collection_idprop[Document]
        breadcrumbs: bpy.types.bpy_prop_collection_idprop[StrProperty]
        is_editing: bool

    @property
    def active_document(self) -> Union[Document, None]:
        return tool.Blender.get_active_uilist_element(self.documents, self.active_document_id)
    
    @property
    def active_referenced_object(self) -> Union[DocumentReferencedObject, None]:
        if self.active_referenced_object_id:
            for obj in self.document_referenced_objects:
                if obj.ifc_definition_id == self.active_referenced_object_id:
                    return obj
        return None
    
