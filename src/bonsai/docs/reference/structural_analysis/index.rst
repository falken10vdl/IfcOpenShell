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
Use **Unlink Physical Element** on a member to remove its link while keeping
the member. Its section and material remain shared until reassigned.