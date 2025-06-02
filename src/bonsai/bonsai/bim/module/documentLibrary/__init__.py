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
from . import ui, prop, operator

classes = (
    operator.AddDocumentLibraryReference,
    operator.AddDocumentLibraryInformation,
    operator.AssignDocumentLibrary,
    operator.DisableDocumentLibraryEditingUI,
    operator.DisableEditingDocumentLibrary,
    operator.EditDocumentLibrary,
    operator.EnableEditingDocumentLibrary,
    operator.LoadDocumentLibrary,
    operator.LoadParentDocumentLibrary,
    operator.LoadProjectDocumentLibraries,
    operator.RemoveDocumentLibrary,
    operator.SelectDocumentLibraryObjects,
    operator.UnassignDocumentLibrary,
    operator.AssignSelectedObjectsToDocumentLibrary,
    operator.RemoveObjectFromDocumentLibraryReference,
    operator.OpenIFCDocumentLibrary,
    prop.DocumentLibraryReferencedObject,
    prop.DocumentLibrary,
    prop.BIMDocumentLibraryProperties,
    ui.BIM_PT_document_libraries,
    ui.BIM_PT_object_document_libraries,
    ui.BIM_UL_document_libraries,
    ui.BIM_UL_document_library_referenced_objects,
    ui.BIM_MT_object_document_libraries_context_menu,

)

def register():
    from bpy.types import VIEW3D_MT_object_context_menu
    
    bpy.types.Scene.BIMDocumentLibraryProperties = bpy.props.PointerProperty(type=prop.BIMDocumentLibraryProperties)
    VIEW3D_MT_object_context_menu.append(ui.add_object_document_libraries_context_menu)

def unregister():
    from bpy.types import VIEW3D_MT_object_context_menu

    VIEW3D_MT_object_context_menu.remove(ui.add_object_document_libraries_context_menu)
    del bpy.types.Scene.BIMDocumentLibraryProperties
