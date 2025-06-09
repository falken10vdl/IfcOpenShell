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
from . import ui, prop, operator, data

classes = (
    operator.AddLibraryReference,
    operator.AddInformation,
    operator.AssignLibrary,
    operator.DisableLibraryEditingUI,
    operator.DisableObjectLibraryEditingUI,
    operator.DisableEditingLibrary,
    operator.EditDocumentLibrary,
    operator.EnableEditingDocumentLibrary,
    operator.LoadLibrary,
    operator.LoadObjectLibraries,
    operator.LoadProjectLibraries,
    operator.RemoveDocumentLibrary,
    operator.SelectLibraryObjects,
    operator.ToggleLibrary,
    operator.UnassignLibrary,
    operator.UpdateAssignedLibraries,
    operator.OpenIFCLibrary,
    operator.UnselectLibrary,
    prop.Library,
    prop.LibraryObject,
    prop.AssignedLibrary,
    prop.ExpandedLibraries,
    prop.BIMDocumentLibraryProperties,
    ui.BIM_PT_documentlibraries,
    ui.BIM_PT_object_libraries,
    ui.BIM_UL_libraries,
    ui.BIM_UL_library_objects,
    ui.BIM_UL_assigned_libraries,
    ui.BIM_MT_object_libraries_context_menu,
)


def register():
    from bpy.types import VIEW3D_MT_object_context_menu

    bpy.types.Scene.BIMDocumentLibraryProperties = bpy.props.PointerProperty(type=prop.BIMDocumentLibraryProperties)
    bpy.types.Scene.ExpandedLibraries = bpy.props.PointerProperty(type=prop.ExpandedLibraries)
    VIEW3D_MT_object_context_menu.append(ui.add_object_libraries_context_menu)


def unregister():
    from bpy.types import VIEW3D_MT_object_context_menu

    VIEW3D_MT_object_context_menu.remove(ui.add_object_libraries_context_menu)
    del bpy.types.Scene.BIMDocumentLibraryProperties
    del bpy.types.Scene.ExpandedLibraries
