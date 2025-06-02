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
import ifcopenshell.util.date
import datetime
from typing import Any, Union, Dict


def edit_information(
    file: ifcopenshell.file, information: ifcopenshell.entity_instance, attributes: Dict[str, Any]
) -> None:
    """Edits the attributes of a library information

    For more information about the attributes, consult the documentation of
    add_information.

    :param information: The IfcLibraryInformation entity you want to edit
    :type information: ifcopenshell.entity_instance
    :param attributes: a dictionary of attribute names and values.
    :type attributes: dict
    :return: None
    :rtype: None

    Example:

    .. code:: python

        # Create a library information
        library = ifcopenshell.api.library.add_information(model)
        
        # Edit the library with new attributes
        ifcopenshell.api.library.edit_information(model,
            information=library,
            attributes={"Name": "ACME Standard Library", "Description": "Updated description"})
    """
    if file.schema == "IFC2X3":
        if "Identification" in attributes:
            # In IFC2X3, Identification is LibraryReference (the 0 index)
            information[0] = attributes["Identification"]
            del attributes["Identification"]

    for name, value in attributes.items():
        # For IFC2X3 or newer versions, handle datetime attributes
        if value and isinstance(value, datetime.datetime):
            # Convert datetime to the appropriate IFC representation
            if name == "LastRevisionDate":
                value = ifcopenshell.util.date.datetime2ifc(value, "IfcCalendarDate")
        
        # Handle version attribute specially if it's a date
        if name == "Version" and value and isinstance(value, datetime.datetime):
            value = ifcopenshell.util.date.datetime2ifc(value, "IfcCalendarDate")
        
        # Set the attribute
        setattr(information, name, value)
