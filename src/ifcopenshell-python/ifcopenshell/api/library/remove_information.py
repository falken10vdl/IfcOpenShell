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
import ifcopenshell.util.element


def remove_information(file: ifcopenshell.file, information: ifcopenshell.entity_instance) -> None:
    """Removes a library information

    :param information: The IfcLibraryInformation entity to remove
    :type information: ifcopenshell.entity_instance
    :return: None
    :rtype: None

    Example:

    .. code:: python

        # Create a library information
        library_info = ifcopenshell.api.library.add_information(model)
        
        # And then remove it
        ifcopenshell.api.library.remove_information(model, information=library_info)
    """
    # Remove any references to this information
    for inverse in file.get_inverse(information):
        if inverse.is_a("IfcRelAssociatesLibrary"):
            file.remove(inverse)
        elif inverse.is_a("IfcLibraryInformationRelationship"):
            if inverse.RelatingLibrary == information:
                file.remove(inverse)
        elif inverse.is_a() == "IfcLibraryReference" and hasattr(inverse, "ReferencedLibrary"):
            inverse.ReferencedLibrary = None
        elif file.schema != "IFC2X3" and hasattr(information, "HasLibraryReferences"):
            # For IFC4 and later, handle HasLibraryReferences
            references = list(information.HasLibraryReferences or [])
            if inverse in references:
                references.remove(inverse)
                if references:
                    information.HasLibraryReferences = references
                else:
                    information.HasLibraryReferences = None

    # Remove the information entity
    file.remove(information)
