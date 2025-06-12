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

A.  **Project Setup** panel in the **Project Overview** tab
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

    In the "Assigned Objects" subpanel, you can also perform the following actions:
    
    .. image:: images/actions_for_assigned_objects.png
    
    1.  Select the object in the 3D viewport that is assigned to the selected document.
    2.  Unassign the selected object from the selected document. This will remove the association between the document and the object.

    If a document has location information then the path to the external document is provided in the "Project Documents" subpanel and two icons allow to inspect it:
    
    .. image:: images/actions_for_documents_with_location.png

    1.  In the case of IFC file it is possible to open the document in a new Blender window.
    2.  In the rest of the cases the URL is opened in the default web browser.


B.  **Misc.** panel in the **Object Information** tab
    If you select and object in the 3D viewport and then select the Misc. panel in the Object Information tab, you will see something like this below:
    
    .. image:: images/actions_for_object_documents.png
    
    In the "Documents" subpanel you will see the list of documents that are associated with the selected object.
    Here you can perform the following actions:

    1. Assign a document from the "Project Documents" panel to the selected object. This will create an association between the document and the object.
    2. If the documetnis an IFC file, you can open it in a new Blender window.
    3. If the document is a URL, you can open it in the default web browser.
    4. You can remove the association between the document and the object.

C.  Context menu in the 3D viewport
    If you right-click on an object in the 3D viewport, you will see a context menu with the option to see the documents this object is assigned to:
    
    .. image:: images/actions_for_context_menu.png

    There you can either open the file in a new Blender window if it is IFC or open the URL in the default web browser.


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


A. **Project Setup** panel in the **Project Overview** tab
    If you select the Libraries panel you will see something like this below:
    
    .. image:: images/libraries_in_project_tab.png

    At the top you have a summary of how many libraries of type "informations" (**IfcLibraryInformation**) and "references" (**IfcLibraryReference**) are in the project and how many objects are assigned.
    
    Then you have two subpanels. 
    
    The upper one ("Project Libraries") shows the list of libraries in the project, where you can create new libraries.
    
    The lower one ("Assigned Objects") shows the list of all objects that are assigned for the library element selected in the row of the upper panel.
    
    Here are the actions that can be performed in this panel:

    .. image:: images/actions_for_assigned_objects_libraries.png

    1.  Add an information library to the project (**IfcLibraryInformation**). This can only be done at root level.
    2.  Add a reference library to the project (**IfcLibraryReference**). This can only be done below an information library.
    3.  Select all objects assigned to the selected library.
    4.  Assign the selected library to the selected objects.
    5.  Edit the selected library. This will open a new panel where you can edit the properties of the library, such as its name, description, and file path.
    6.  Remove the selected library and its children from the project. This will remove the library(s) and all its associations with objects.

    In the "Assigned Objects" subpanel, you can also perform the following actions:
    
    .. image:: images/actions_for_assigned_objects_for_libraries.png
    
    1.  Select the object in the 3D viewport that is assigned to the selected library.
    2.  Unassign the selected object from the selected library. This will remove the association between the library and the object.

    If a library has location information then the path to the external document is provided in the "Project Libraries" subpanel and two icons allow to inspect it:
    
    .. image:: images/actions_for_libraries_with_location.png

    1.  In case of IFC file it is possible to open it in a new Blender window.
    2.  In case of URL it is possible to open it in a default web browser.

B. **Misc.** panel in the **Object Information** tab
    If you select and object in the 3D viewport and then select the Misc. panel in the Object Information tab, you will see something like this below:
    
    .. image:: images/actions_for_object_libraries.png
    
    In the "Libraries" subpanel you will see the list of libraries that are associated with the selected object.
    Here you can perform the following actions:

    1.  Assign a library from the "Project Libraries" panel to the selected object. This will create an association between the library and the object.
    2.  If the library is an IFC file, you can open it in a new Blender window.
    3.  If the library is a URL, you can open it in the default web browser.
    4.  You can remove the association between the library and the object.


C. Context menu in the 3D viewport
    If you right-click on an object in the 3D viewport, you will see a context menu with the option to see the libraries this object is assigned to:
    
    .. image:: images/actions_for_context_menu_libraries.png

    There you can either open the file in a new Blender window if it is IFC or open the URL in the default web browser.


Use Case: Implementing LoD (Levels of Detail) using Documents and Libraries
----------------------------------------------------------------------------

We can use documents and libraries to implement simple Levels of Detail (LoD) in our BIM models.
The idea is to use documents and/or libraries to link other IFC files which provide additional levels of detail for the same objects or its subcomponents.

Let's see this with an example:
Imagine we have a building model with walls, windows, and doors. We want to provide different levels of detail for these elements.
We can create a document that references an IFC file with the detailed geometry of the walls, windows, and doors.

TBC.
