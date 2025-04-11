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

# ############################################################################ #

# Hey there! Welcome to the Bonsai code. Please feel free to reach
# out if you have any questions or need further guidance. Happy hacking!

# ############################################################################ #

# Every module has a prop.py file to define Blender properties. Any time you
# want an interface widget like an input field, dropdown, checkbox, or number
# slider, you need a Blender property to store that widget's data. If you want
# to store data that will affect the Blender interface, you also need a
# property. Properties are stored in the .blend file, so when your user closes
# their Blender session, and reopens it, things are how they left it.

import bpy
from bpy.props import (
    PointerProperty,
    StringProperty,
    BoolProperty,
    CollectionProperty,
)



# ---------------------------------------------
# Node Class
# ---------------------------------------------
class FileNode(bpy.types.PropertyGroup):
    name: StringProperty()
    full_path: StringProperty()
    parent_name: StringProperty()
    is_directory: BoolProperty()
    enabled: BoolProperty()
    expanded: BoolProperty(default=False)

# ---------------------------------------------
# Tree Class
# ---------------------------------------------
class FileTree(bpy.types.PropertyGroup):
    nodes: CollectionProperty(type=FileNode)

# Add a property to manage the visibility of linked files
bpy.types.Scene.show_linked_files = BoolProperty(default=False)