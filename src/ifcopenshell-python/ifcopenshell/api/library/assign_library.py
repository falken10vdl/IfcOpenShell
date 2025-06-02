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
import ifcopenshell.api.owner
import ifcopenshell.guid
import ifcopenshell.util.element
from typing import Union, List, Optional


def assign_library(
    file: ifcopenshell.file,
    products: List[ifcopenshell.entity_instance] = None,
    library: Optional[ifcopenshell.entity_instance] = None,
    should_run_listeners: bool = True,
) -> Union[ifcopenshell.entity_instance, None]:
    """Assigns a library to a list of products

    An object may be assigned to zero, one, or multiple libraries. Almost
    any object or property may be assigned to a library, though typically
    this is used for types, physical products and properties.
    Adding a new assignment is typically done using a library reference and
    an object.

    :param products: The list of objects to associate the library to. This could be
        almost any sensible object in IFC.
    :param library: The IfcLibraryReference or IfcLibraryInformation to associate to.
    :return: The IfcRelAssociatesLibrary relationship
        or `None` if `products` was an empty list or all products were
        already assigned to the `library`.

    Example:

    .. code:: python

        library = ifcopenshell.api.library.add_information(model)
        ifcopenshell.api.library.edit_information(model,
            information=library,
            attributes={"Name": "StandardsLibrary", "Version": "1.0"})
        reference = ifcopenshell.api.library.add_reference(model, library=library)

        # Let's imagine door_type represents an IfcDoorType
        ifcopenshell.api.library.assign_library(model, products=[door_type], library=reference)
    """
    if not products or library is None:
        return None

    # Get elements already referenced by this library
    referenced_elements = ifcopenshell.util.element.get_referenced_elements(library)
    products_set: set[ifcopenshell.entity_instance] = set(products)
    products_set = products_set - referenced_elements

    if not products_set:
        return None

    # Try to find existing relationship
    if file.schema == "IFC2X3":
        rel = next(
            (r for r in file.by_type("IfcRelAssociatesLibrary") if r.RelatingLibrary == library),
            None,
        )
    else:
        ifc_class = library.is_a()
        if ifc_class == "IfcLibraryReference":
            rel = next((r for r in file.by_type("IfcRelAssociatesLibrary") 
                       if r.RelatingLibrary == library), None)
        elif ifc_class == "IfcLibraryInformation":
            rel = next((r for r in file.by_type("IfcRelAssociatesLibrary") 
                       if r.RelatingLibrary == library), None)
        else:
            assert False, f"Unexpected library type: {ifc_class}"

    if not rel:
        return file.create_entity(
            "IfcRelAssociatesLibrary",
            GlobalId=ifcopenshell.guid.new(),
            OwnerHistory=ifcopenshell.api.owner.create_owner_history(file),
            RelatedObjects=list(products_set),
            RelatingLibrary=library,
        )

    related_objects = set(rel.RelatedObjects) | products_set
    rel.RelatedObjects = list(related_objects)
    ifcopenshell.api.owner.update_owner_history(file, element=rel)
    return rel
