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


def unassign_library(file, products=None, library=None):
    """Unassign a library from products
    
    Removes an assignment of an IfcLibraryInformation from one or more products.
    
    :param products: The products to unassign the library from.
    :type products: list[ifcopenshell.entity_instance]
    :param library: The library information to unassign.
    :type library: ifcopenshell.entity_instance
    :return: None
    :rtype: None
    
    Example:
    
    .. code:: python
        
        # Get a library information
        library_info = model.by_type("IfcLibraryInformation")[0]
        
        # Unassign it from a wall
        wall = model.by_type("IfcWall")[0]
        ifcopenshell.api.run("library.unassign_library", model, products=[wall], library=library_info)
    """
    if products is None:
        products = []
        
    if not library.is_a("IfcLibraryInformation"):
        return
        
    # Find relationships that associate our library with products
    for rel in file.by_type("IfcRelAssociatesLibrary"):
        if rel.RelatingLibrary != library:
            continue
            
        # Check if any of our products are in this relationship
        related_objects = set(rel.RelatedObjects or [])
        products_to_remove = set(products)
        
        # Find intersection of products in relationship
        common_products = related_objects.intersection(products_to_remove)
        
        if not common_products:
            # None of our products are in this relationship
            continue
            
        # Remove our products from the relationship
        remaining_products = related_objects - products_to_remove
        
        if remaining_products:
            # Update relationship with remaining products
            rel.RelatedObjects = list(remaining_products)
        else:
            # No products left, delete the relationship
            file.remove(rel)
