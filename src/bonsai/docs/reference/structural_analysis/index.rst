Structural Analysis
===================

.. include:: /_incomplete_message.rst


.. figure:: images/interface_property-editor_structural-analysis.png
   :alt: property editor structural analysis sub-tab

   Structural Analysis sub-tab.

Generated member sections
-------------------------

Generated curve members share their section profile and material with their
physical beam or column. Editing shared data may also affect other elements
using the same type. The member details identify shared values.

Generation requires an extruded section and either a single material or a
single-profile material set. Elements without them are skipped with a
warning. IFC2X3 structural model generation is not supported.

Material removal is blocked while linked structural members depend on it.
Each member row shows a checkmark when both assignments are present and its
linked source matches, or a warning with details of missing assignments or
source changes. Hover over the warning for differences and tolerances.
The X removes the member and connections no longer used by another member;
the physical beam or column is preserved.
In the member details, click
the chain icon beside Section or Material to remove that assignment from the
member, or the broken chain to choose an existing profile or material. Removing
an assignment does not alter the physical element or its link to the member.
An incomplete member is not automatically filled in by later physical-element
edits; select its physical beam or column and use **(Re)Generate from Selected**
to synchronize it again. Other selected objects are ignored.
Section changes also refresh the geometry of loaded physical elements using
the shared profile set.
For multi-profile members or other material sets, use the material editor to
change individual items.