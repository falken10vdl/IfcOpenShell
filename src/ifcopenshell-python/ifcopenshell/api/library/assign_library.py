# IfcOpenShell - IFC toolkit and geometry engine
# Copyright (C) 2021 Dion Moult <dion@thinkmoult.com>
#
# This file is part of IfcOpenShell.
#
# IfcOpenShell is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# IfcOpenShell is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with IfcOpenShell.  If not, see <http://www.gnu.org/licenses/>.

import ifcopenshell
import ifcopenshell.api.owner.settings


def assign_library(file, products=None, library=None):
    """Assign a library to products
    
    Assigns an IfcLibraryInformation to one or more products.
    
    :param products: The products to assign the library to.
    :type products: list[ifcopenshell.entity_instance]
    :param library: The library information to assign.
    :type library: ifcopenshell.entity_instance
    :return: The newly created IfcRelAssociatesLibrary
    :rtype: ifcopenshell.entity_instance
    
    Example:
    
    .. code:: python
        
        # Create a new library information
        library_info = ifcopenshell.api.run("library.add_library", model, name="Product Catalog")
        
        # Assign it to a wall element
        wall = model.by_type("IfcWall")[0]
        ifcopenshell.api.run("library.assign_library", model, products=[wall], library=library_info)
    """
    if products is None:
        products = []
        
    if not library.is_a("IfcLibraryInformation"):
        return None
    
    # Check if a relationship already exists for this library
    for rel in file.by_type("IfcRelAssociatesLibrary"):
        if rel.RelatingLibrary == library:
            # Add products to existing relationship
            related_objects = set(rel.RelatedObjects or [])
            related_objects.update(products)
            rel.RelatedObjects = list(related_objects)
            return rel
            
    # Create a new relationship if none exists
    owner = ifcopenshell.api.owner.settings.get_user(file)
    
    return file.create_entity(
        "IfcRelAssociatesLibrary",
        GlobalId=ifcopenshell.guid.new(),
        OwnerHistory=file.by_type("IfcOwnerHistory")[0] if file.by_type("IfcOwnerHistory") else None,
        RelatingLibrary=library,
        RelatedObjects=products
    )
