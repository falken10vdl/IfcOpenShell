Referencing documents and libraries
===================================

Within IFC it is possible to reference other documents and libraries. 

This is useful for linking to external documents such as specifications, standards, or
other resources that are relevant to the project. It can also be used to reference other
IFC files which allows for the creation of a federated model where multiple disciplines can work together
on a project or different levels of detail can be provided for different purposes.

There are two types of elements for this matter: documents and libraries.

These external elements can be associated with the current project or with specific
objects within the project. Derived classed from **IfcRelAssociates**: **IfcRelAssociatesDocument** and **IfcRelAssociatesLibrary** are used for
this purpose.

Documents and Libraries are implemented using "information" objects (derived from **IfcExternalInformation**: **IfcDocumentInformation** 
and **IfcLibraryInformation**) and "reference" objects (derived from **IfcExternalReference**: **IfcDocumentReference** and **IfcLibraryReference**).

References are always associated with information objects. An Information element can have 0, 1 or multiple references, but a 
reference can only be associated with one information element.

Documents allow for a tree structure by means of **IfcDocumentInformationRelationship** which enables a document information element to have
the ability to reference other document information element.
This means that you can create a hierarchy of documents, where the root information documents (**IfcDocumentInformation**) have 
**IfcRelAssociatesDocument** relationships to **IfcProject** and or other Ifc objects and the child information documents (**IfcDocumentInformation**) 
have **IfcDocumentInformationRelationship** relationships to other **IfcDocumentInformation** elements.
For any **IfcDocumentInformation** element, you can have multiple **IfcDocumentReference**


Libraries allow for a flat structure, meaning that a library information element cannot reference other library information elements.
This means that you have a number of root library information elements (**IfcLibraryInformation**) that have **IfcRelAssociatesLibrary** 
relationships to other Ifc objects.
For any **IfcLibraryInformation** element, you can have multiple **IfcLibraryReference**.

In Bonsai, you can create and manage these documents and libraries within three differente places:

- The **Project Setup** panel in the **Project Overview** tab. This is where you can create and update documents and libraries, and manage their associations with specific objects.
- The **Misc.** panel in the **Object Information** tab. This is where you can focus for a selected Object in the documents and libraries associated with it.
- The context menu that appears when you right-click on the 3D viewport. This is a convenient productivity shortcut to view and open the documents and libraries for a selected object.


Documents
---------

"IfcDocuments" ( **IfcDocumentInformation** and **IfcDocumentReference**). 

Serve to describe and reference external documents that provide supporting 
information for the BIM model, such as: PDFs, Technical reports, Contracts, Drawings, Certifications, etc.

Documents support traceability, compliance, and communication (ex. linking a slab to its installation guide).

Example Use Cases:

- Link a structural slab to its PDF specification
- Attach fire safety certificates to building storeys
- Reference maintenance manuals for equipment

1.  **Project Setup** panel in the **Project Overview** tab
    If you select the Documents panel you will see something like this below:
    
    .. image:: images/documents_in_project_tab.png

    At the top you have a summary of how many documents of type "informations" (**IfcDocumentInformation**) and "references" (**IfcDocumentReference**) are in the project and how many objects are assigned.
    
    Then you have two subpanels. 
    
    The upper one ("Project Documents") shows the tree structure of the documents in the project, where you can create new documents and manage their hierarchy.
    
    The lower one ("Assigned Objects") shows the list of all objects that are assigned for the document element selected in the row of the upper panel.
    
    Here are the actions that can be performed in this panel:

    .. image:: images/actions_for_documents.png

    1.  Add an information document to the project (**IfcDocumentInformation**). This can only be done at root level or below another information document.
    2.  Add a reference document to the project (**IfcDocumentReference**). This can only be done below an information document.
    3.  Select all objects assigned to the selected document.
    4.  Assign the selected document to the selected objects.
    5.  Edit the selected document. This will open a new panel where you can edit the properties of the document, such as its name, description, and file path.
    6.  Remove the selected document and its children from the project. This will remove the document(s) and all its associations with objects.


2.  **Misc.** panel in the **Object Information** tab

3.  Context menu in the 3D viewport

Libraries
---------

"IfcLibraries" ( **IfcLibraryInformation** and **IfcLibraryReference**). 

Serve to describe and reference external libraries that provide supporting 
information for the BIM model, such as: Manufacturer catalogs, BIM object libraries, National or international standards, etc.

Libraries promote standardization, parametric modeling, and manufacturer integration (ex. choosing a window type from a certified catalog).

Example Use Cases:

- Link a door type to a library of standard door profiles
- Associate a steel beam with its EN standard profile from a national catalog
- Reuse standardized assemblies across multiple projects


Use Case: Implementing LoD (Levels of Detail) using Documents and Libraries
----------------------------------------------------------------------------

We can use documents and libraries to implement simple Levels of Detail (LoD) in our BIM models.
The idea is to use documents and/or libraries to link other IFC files which provide additional levels of detail for the same objects or its subcomponents.

Let's see this with an example:
Imagine we have a building model with walls, windows, and doors. We want to provide different levels of detail for these elements.
We can create a document that references an IFC file with the detailed geometry of the walls, windows, and doors.


    IFC2X3 models cannot be georeferenced. There is a proposed convention to
    provide fallback support but this is not supported yet in any known vendor.
    Please consider upgrading to IFC4.

Most architects and engineers will know the name of the **Projected CRS**
typically chosen by the surveyor. For example in Sydney, Australia, you might
use GDA2020 / MGA Zone 56. In IFC a standardised code from the EPSG public
registry is used to refer to the **Projected CRS**. For example, GDA 2020 / MGA
Zone 56 will be named EPSG:7856.

You can check whether or not your model is georeferenced in the **IFC
Georeferencing** panel in the **Scene Properties** tab. You should see a section
for the **Projected CRS** with an EPSG code.

.. image:: images/projectedcrs.png

If you do not see this, your project is not georeferenced.

.. Note::

    Even if a model has large "real world coordinates", this does not mean the
    project is georeferenced. Without a **Projected CRS**, these coordinates are
    meaningless.

Map conversions
---------------

The coordinates for the nominated **Projected CRS** are known as **Map
Coordinates**. These **Map Coordinates** are typically large numbers and read as
Eastings and Northings.

In vertical construction, some disciplines (such as a civil engineer or
surveyor) will directly use **Map Coordinates** in their designs. Most others,
such as the architect, structural, and service engineers will instead use
**Local engineering coordinates**. A **Map Conversion** stores the parameters
for transforming **Local engineering coordinates** to **Map Coordinates**.

For example, a civil engineer will work directly in **Map Coordinates**. This
means that the model's coordinates correlate directly to Eastings and
Northings.  Similarly, the model's +Y axis will point to **Grid North**.  As
there is no **Map Conversion** involved, you will see a 0 in the Eastings,
Northings, and Orthogonal Height in the **IFC Georeferencing** panel.

.. image:: images/mapcoordinates.png

When **Local engineering coordinates** are used, typically the architect will
nominate a local origin and model geometry will be drawn orthogonally (i.e.
along the X and Y axis). This local origin often correlates with a site boundary,
surveyed point, or grid intersection. This means that the model's coordinates
are typically smaller numbers and correlate to surface distance measurements,
not Eastings and Northings, and the model's +Y axis will point to **Project
North**. The surveyor will then provide the necessary **Map Conversion**
parameters to convert from **Local engineering coordinates** to Eastings,
Northings, Orthogonal Height, and **Grid North**.

.. image:: images/mapconversion.png

.. warning::

    Coordinate systems are a technical topic. A common error is that disciplines
    may choose to use **Map Coordinates** without realising that map distances
    do not correlate with surface distances measured on the ground.  Unless you
    are trained to work in **Map Coordinates**, it is safer to work with local
    engineering coordinates and consult your surveyor for professional guidance.

**Map Conversions** contain six parameters.

**Eastings**, **Northings** and **Orthogonal Height** parameters define the
translation from the model's XYZ coordinates to map **Eastings**, **Northings**,
and **Heights**.  Your model's local engineering origin at 0, 0, 0, will always
convert exactly to the **Easting**, **Northing**, and **Orthogonal Height**
displayed in this panel.

The **X Axis Abcissa** and **X Axis Ordinate** define the rotation vector from
**Project North** to **Grid North**. These two numbers combine into a coordinate
vector pointing along the X axis (i.e. **Project East**). The default is an
abscissa of 1 and ordinate of 0. This default (1, 0) vector implies **Project
East** and **Grid East** coalign, which means there is no rotation between
**Project North** and **Grid North**.

.. image:: images/xaxisabscissaordinate.png

.. tip::
    
   To save you the mental struggle of converting to degrees, a calculated
   rotation is always just below these values. Phew!

The distance measured on site, or the "surface distance" is actually not the
same as the distance measured between Eastings and Northings. This difference is
provided by the **Scale** parameter. The **Scale** defines the average combined
scale factor across the small 1km site that converts from the model's surface
distances to map grid distances. Note that the **Scale** is actually not a
constant. However, for the small sites dealt with in vertical construction, it
may be approximated to be a constant by your surveyor and will typically be a
value close to, but not exactly 1.

.. note::

    Always check that the surveyor provides a scale factor such that surface
    distance multiplied by **Scale** equals map grid distances (as opposed to
    the other way around).

Working with Map Coordinates
----------------------------

Bonsai is designed to work with small coordinates (under 1km), whereas map
coordinates are typically large. When you load an IFC which uses map
coordinates directly, or when you are working with IFC2X3 and you cannot use a
map conversion, Bonsai will autodetect a point on your model to use as a false
origin.

The XYZ offset used for the false origin will be shown in the **IFC
Georeferencing** panel under the **Blender Offset** header. It
is very similar to a **Map Conversion**, but it will not have a scale and only
temporarily affects your Blender session.

.. image:: images/blenderoffset.png

.. note::

    A Blender offset is simply a shift in coordinates to reduce large model
    coordinates to smaller coordinates. It should not be used as an indicator of
    whether georeferencing is done correctly. Always check the **Projected
    CRS**, **Map Conversion** and confirm the parameters with your surveyor.

This distance limit of 1km and autodetected false origin may not be appropriate
for your project. For example, your project may exceed the 1km limit, or you may
want to federate multiple files together and manually specify a consistent and
fixed false origin. You can customise these options by choosing
:ref:`Enable Advanced Mode <Project Info Advanced Loading Mode>`  when loading a project.
Then, set the **Distance Limit** (in meters) and the **False Origin** coordinate
before pressing **Load Project Elements**.

.. image:: images/manualorigin.png

When a false origin is used, there are two possible methods to offset objects by
the false origin.

The first method is to offset the origin point of objects. We call this the
**Object Placement** method.  The second method is to offset the local
coordinates of geometry within the objects themselves. We call this the
**Cartesian Point** method. Sometimes, BIM applications combine both of these
methods in a single IFC project. To see which workaround was used on an object,
check the "Blender Offset" property in the **Transform** panel in the **Object
Properties**. This is an advanced property used by powerusers to debug
coordinate issues and may be safely ignored by most users.

.. image:: images/offsetmode.png

Incorrect coordinate use
------------------------

Sometimes, a model may mix **Map Coordinates** and **Local engineering
coordinates**. For example, a surveyed pipe may have its placement use **Map
Coordinates** with large Eastings and Northings. However, the placement of the
site object may be still set at 0, 0, 0. Since this range of coordinates exceed
the default 1km distance limit, this creates a problem. Blender needs to choose
between displaying the pipe accurately and sacrificing precision at the site
placement, or vice versa, but it is impossible to satisfy both simultaneously in
the same Blender session.

.. warning::

    Many IFC viewers only show geometry, and don't show object placements. This may
    give users the false impression that their coordinates in their IFC project
    do not have such a large range. However, as a native IFC authoring platform,
    Bonsai will not accept this inconsistency.

At this point, it is the users responsibility to reconcile this inconsistency in
their coordinates. Either the user needs to fix their file to consistently
offset all coordinates, or the user needs to manually tell Bonsai the
coordinates of the desired false origin and accept the precision loss.

Converting local and map coordinates
------------------------------------

You can convert **Local engineering coordinates** to **Map coordinates** and
vice versa in the **Viewport** panel. First, enable ``View > Sidebar`` then type
in your coordinate in the **Input** field. Press either the **Local to Global**
or **Global to Local** button to convert the coordinate. You will see the result
of the calculation in the **Output** field.

.. image:: images/coordinateconversion.png

True north
----------

When **Local engineering coordinates** are used, the model's +Y axis points to
**Project North** for the convenience of drafting. When **Map Coordinates** are
used, the model's +Y axis points to **Grid North** for the necessity of
surveying.

**Project North** and **Grid North** is different to **True North**. The angle
to **True North** is not a fixed angle. It will actually vary depending on the
Eastings and Northings you choose to calculate it from.

However, this variable **True North** is a great source of confusion to
architects, who typically just want to do a shadow study, solar study, or
similar and go out for an early lunch. IFC can store a fixed **True North**
value as a reference to be used for these types of usecases. If one is stored in
your project, you may see it under the **True North** section of the **IFC
Georeferencing** panel. Your surveyor will be able to provide the **True North**
vector, but it should be only used as a reference, never used as a way to
coordinate model rotations, and always with the understanding that it is not a
fixed value.

.. image:: images/truenorth.png

.. warning::

   Fun fact: **Magnetic North** is useless for the purposes of construction.

Coordinate precision limits
---------------------------

Bonsai focuses on vertical construction. Vertical construction typically uses
**Local engineering coordinates** on a small site. The buildingSMART
georeferencing technical experts panel have determined that a small site under
1km square can be assumed to have a constant **Map Conversion**.

Therefore, if your model is less than 1km square, you are within the coordinate
precision limits. This is where the 1km default distance limit is derived from.

If you want to exceed the 1km square surveying limitation, you will need to be
aware of software limitations that can result in precision loss when large
coordinate ranges are used.

Blender, and subsequently Bonsai, is not designed for **Map Coordinates**.
Blender internally uses single precision floating point calculations. A full
description of the precision implications are described in the `Blender working
limits documentation
<https://docs.blender.org/manual/en/latest/advanced/limits.html>`__.

This means that lengths greater than 5,000 meters start to accumulate software
precision errors that affect the nearest millimeter. Therefore, from a software
perspective, it is unwise to embark on a project with coordinates ranging
greater than +/- 5km.
