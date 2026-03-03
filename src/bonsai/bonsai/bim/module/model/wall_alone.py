# Bonsai - OpenBIM Blender Add-on
# Copyright (C) 2020, 2021 Dion Moult <dion@thinkmoult.com>
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
#
# This file was generated with the assistance of an AI coding tool.

"""WallAlone — a single IfcWall defined by an open or closed 2-D polyline
that acts as the horizontal axis/directrix, swept with a rectangular
cross-section (wall thickness × wall height) in the vertical direction.

Unlike a slab (which requires a closed footprint), the polyline here may be
open; the user decides whether to close the loop or not.

IFC representation strategy
---------------------------
Body:  IfcSurfaceCurveSweptAreaSolid  (RepresentationType = "SweptSolid")
         SweptArea        = IfcRectangleProfileDef (thickness × height)
         Directrix        = IfcIndexedPolyCurve
                              ├─ IfcCartesianPointList2D
                              └─ Segments: IfcLineIndex (straight) | IfcArcIndex (3-pt arc)
         ReferenceSurface = IfcPlane  (the XY plane; normal = (0,0,1))
Axis:  Plan/Axis/GRAPH_VIEW  — projection of the directrix onto XY

Requires IFC4 or later — IFC2X3 is not supported.

Edit-mode tools (via the slab-style CAD polyline editor):
    Extend, Join, Fillet, 3-point arc, …  (ProfileDecorator + bim.cad_tool)
    → edits the axis/directrix, not a closed profile
    Arc triplets are marked with IFCARCINDEX vertex groups.

Object-mode tools:
    • Extend Height  – change the vertical extrusion depth
    • Add Void       – insert an opening in the wall body

Toggle Openings (from the openings panel in the sidebar).
"""

import math
from math import isclose

import bpy
import ifcopenshell.util.shape_builder
import ifcopenshell
import ifcopenshell.api.feature
import ifcopenshell.api.geometry
import ifcopenshell.api.material
import ifcopenshell.api.pset
import ifcopenshell.api.root
import ifcopenshell.api.type
import ifcopenshell.util.element
import ifcopenshell.util.placement
import ifcopenshell.util.representation
import ifcopenshell.util.type
import ifcopenshell.util.unit
from mathutils import Matrix, Vector

import bonsai.core.geometry
import bonsai.core.root
import bonsai.tool as tool
from bonsai.bim.ifc import IfcStore
from bonsai.bim.module.model.decorator import (
    PolylineDecorator,
    ProductDecorator,
    ProfileDecorator,
)
from bonsai.bim.module.model.polyline import PolylineOperator

# ---------------------------------------------------------------------------
# Engine tag written to EPset_Parametric so the system can identify
# WallAlone objects.
# ---------------------------------------------------------------------------
WALL_ALONE_ENGINE = "Bonsai.WallAlone"


def _is_wall_alone_element(element: ifcopenshell.entity_instance) -> bool:
    """Return True if *element* is a WallAlone wall.

    OCC boolean operations on IfcSurfaceCurveSweptAreaSolid are unreliable,
    so openings on WallAlone walls must be applied via Blender boolean
    modifiers instead of the geometry engine.
    """
    psets = ifcopenshell.util.element.get_psets(element)
    return psets.get("EPset_Parametric", {}).get("Engine") == WALL_ALONE_ENGINE


def _ensure_wall_alone_modifier(
    wall_obj: bpy.types.Object, opening_obj: bpy.types.Object
) -> None:
    """Add a Blender BOOLEAN modifier on *wall_obj* for *opening_obj* if absent."""
    mod_name = f"Opening_{opening_obj.name}"
    if mod_name not in wall_obj.modifiers:
        mod = wall_obj.modifiers.new(name=mod_name, type="BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.object = opening_obj
        mod.solver = "FLOAT"


def _setup_all_wall_alone_modifiers(
    wall_obj: bpy.types.Object,
    wall_element: ifcopenshell.entity_instance,
    hide: bool = True,
) -> None:
    """Re-add Blender boolean modifiers for every opening on a WallAlone wall.

    Call after ``switch_representation`` which clears all modifiers.
    If *hide* is True the opening objects are hidden (default for non-editing state).
    """
    openings = [rel.RelatedOpeningElement for rel in getattr(wall_element, "HasOpenings", [])]
    if not openings:
        return
    to_load = [o for o in openings if not tool.Ifc.get_object(o)]
    if to_load:
        tool.Model.load_openings(to_load)
    for opening_element in openings:
        opening_obj = tool.Ifc.get_object(opening_element)
        if not opening_obj:
            continue
        _ensure_wall_alone_modifier(wall_obj, opening_obj)
        if hide:
            opening_obj.hide_viewport = True
            opening_obj.hide_render = True


# ---------------------------------------------------------------------------
# Display helpers: convert IfcIndexedPolyCurve arcs to IfcTrimmedCurve/IfcCircle
# ---------------------------------------------------------------------------


def _circumcenter_2d(p1, p2, p3):
    """Return the (cx, cy) circumcenter of the triangle, or None if the points are collinear."""
    ax, ay = p1
    bx, by = p2
    cx, cy = p3
    d = 2.0 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-10:
        return None
    ux = ((ax**2 + ay**2) * (by - cy) + (bx**2 + by**2) * (cy - ay) + (cx**2 + cy**2) * (ay - by)) / d
    uy = ((ax**2 + ay**2) * (cx - bx) + (bx**2 + by**2) * (ax - cx) + (cx**2 + cy**2) * (bx - ax)) / d
    return (ux, uy)


def _make_display_axis_items(ifc_file, directrix):
    """Convert an IfcIndexedPolyCurve (with IfcArcIndex/IfcLineIndex segments) into
    a list of IFC curve entities for direct use in IfcShapeRepresentation.Items.

    - IfcLineIndex segments  → IfcPolyline
    - IfcArcIndex  segments  → IfcTrimmedCurve backed by IfcCircle

    This mirrors the approach used by the door swing arc so that Blender's
    viewport renders smooth arcs instead of bare control points.
    """
    coords = list(directrix.Points.CoordList)

    def get_pt(idx):  # IFC indices are 1-based
        return coords[idx - 1]

    if not directrix.Segments:
        # Plain polyline — no arc data; emit a single IfcPolyline.
        pts = [ifc_file.createIfcCartesianPoint(list(c)) for c in coords]
        return [ifc_file.createIfcPolyline(pts)]

    items = []
    for seg in directrix.Segments:
        if seg.is_a("IfcLineIndex"):
            indices = list(seg[0])
            pts = [ifc_file.createIfcCartesianPoint(list(get_pt(i))) for i in indices]
            items.append(ifc_file.createIfcPolyline(pts))
        elif seg.is_a("IfcArcIndex"):
            i1, i2, i3 = seg[0]
            p1 = get_pt(i1)
            pmid = get_pt(i2)
            p3 = get_pt(i3)
            center = _circumcenter_2d(p1, pmid, p3)
            if center is None:
                # Collinear — fall back to a polyline through the three points.
                pts = [ifc_file.createIfcCartesianPoint(list(p)) for p in (p1, pmid, p3)]
                items.append(ifc_file.createIfcPolyline(pts))
                continue
            cx, cy = center
            radius = math.hypot(p1[0] - cx, p1[1] - cy)
            # Determine arc sense: CCW (SenseAgreement=True) if cross(C→P1, C→Pmid) > 0.
            v1 = (p1[0] - cx, p1[1] - cy)
            vmid = (pmid[0] - cx, pmid[1] - cy)
            sense = (v1[0] * vmid[1] - v1[1] * vmid[0]) > 0
            placement_2d = ifc_file.createIfcAxis2Placement2D(
                Location=ifc_file.createIfcCartesianPoint([cx, cy])
            )
            circle = ifc_file.createIfcCircle(Position=placement_2d, Radius=radius)
            trim1 = [ifc_file.createIfcCartesianPoint(list(p1))]
            trim2 = [ifc_file.createIfcCartesianPoint(list(p3))]
            trimmed = ifc_file.createIfcTrimmedCurve(
                BasisCurve=circle,
                Trim1=trim1,
                Trim2=trim2,
                SenseAgreement=sense,
                MasterRepresentation="CARTESIAN",
            )
            items.append(trimmed)
    return items


# ---------------------------------------------------------------------------
# Geometry generator
# ---------------------------------------------------------------------------


class DumbWallAloneGenerator:
    """Creates a single IfcWall swept along an open or closed 2-D polyline.

    The polyline is the horizontal axis/directrix of the wall.
    A rectangular cross-section (wall thickness × wall height) is swept along
    it using IfcSurfaceCurveSweptAreaSolid so the cross-section stays upright.

    The user is free to draw an open or a closed polyline; no closure is forced.

    Contrast with:
        DumbSlabGenerator  →  IfcSlab,  closed footprint extruded vertically
        DumbWallGenerator  →  IfcWall,  straight LAYER2 axis-based wall
        DumbWallAloneGenerator  →  IfcWall,  polyline-axis directrix sweep
    """

    def __init__(self, relating_type: ifcopenshell.entity_instance):
        self.relating_type = relating_type

    def generate(self, insertion_type: str = "POLYLINE"):
        """Entry point.  Returns the created Blender object or None."""
        self.file = tool.Ifc.get()
        self.unit_scale = ifcopenshell.util.unit.calculate_unit_scale(self.file)

        # Verify the type has a usable material layer set
        thicknesses = self._get_layer_thicknesses()
        if not sum(thicknesses):
            return None

        self.body_context = ifcopenshell.util.representation.get_context(
            self.file, "Model", "Body", "MODEL_VIEW"
        )
        # Axis representation (Plan view) stores the 2-D directrix polyline;
        # used by plan drawings and by the edit-axis workflow.
        self.axis_context = ifcopenshell.util.representation.get_context(
            self.file, "Plan", "Axis", "GRAPH_VIEW"
        )

        props = tool.Model.get_model_props()

        self.polyline = None  # list of (x, y[, z]) tuples in local coords
        self.container = None
        self.container_obj = None
        if container := tool.Root.get_default_container():
            self.container = container
            self.container_obj = tool.Ifc.get_object(container)

        self.height = props.extrusion_depth  # vertical extrusion height (Z)
        self.thickness = sum(self._get_layer_thicknesses()) * self.unit_scale
        self.x_angle = 0 if tool.Cad.is_x(props.x_angle, 0, tolerance=0.001) else props.x_angle
        self.location = Vector((0, 0, 0))

        if insertion_type == "POLYLINE":
            return self._derive_from_polyline()
        elif insertion_type == "CURSOR":
            return self._derive_from_cursor()
        return None

    # ------------------------------------------------------------------
    # Insertion helpers
    # ------------------------------------------------------------------

    def _derive_from_polyline(self):
        """Read the directrix from the active PolylineOperator data.

        The polyline may be open or closed — no closure is forced.  The user
        decides the topology by whether the last point coincides with the first.
        A minimum of 2 points is required (one segment).
        """
        polyline_props = tool.Model.get_polyline_props()
        polyline_data = polyline_props.insertion_polyline
        polyline_points = polyline_data[0].polyline_points if polyline_data else []

        if len(polyline_points) < 2:
            return None

        self.location = Vector(
            (polyline_points[0].x, polyline_points[0].y, self.container_obj.location.z if self.container_obj else 0.0)
        )
        # Polyline coordinates in the local XY plane relative to the object origin.
        # Z is kept at 0.0 — the height is handled by the sweep, not the path.
        self.polyline = [
            tuple(Vector((p.x, p.y, 0.0)) - self.location) for p in polyline_points
        ]
        # NOTE: do NOT force closure here.  If the user closed the polyline the
        # last point will already equal the first; otherwise the wall stays open.

        return self._create_wall_alone()

    def _derive_from_cursor(self):
        """Placeholder: create a default rectangular WallAlone at the cursor.

        TODO: implement a sensible default shape (e.g. 3 m × 0.2 m rectangle).
        """
        raise NotImplementedError("Cursor insertion for WallAlone is not yet implemented.")

    # ------------------------------------------------------------------
    # IFC / Blender object creation
    # ------------------------------------------------------------------

    def _create_wall_alone(self) -> bpy.types.Object:
        """Create the Blender object and associated IFC entities.

        Body representation
        -------------------
        IfcSurfaceCurveSweptAreaSolid  (RepresentationType = "SweptSolid")
            SweptArea        = IfcRectangleProfileDef (thickness × height)
            Directrix        = IfcIndexedPolyCurve  (self.polyline in local XY)
            ReferenceSurface = IfcPlane at the XY plane (normal = (0,0,1))

        The XY reference surface keeps the rectangle upright: the plane's
        Z-normal drives the height axis of the swept cross-section.
        """
        ifc_class = self._get_ifc_class()

        mesh = bpy.data.meshes.new("Dummy")
        obj = bpy.data.objects.new(
            tool.Model.generate_occurrence_name(self.relating_type, ifc_class), mesh
        )

        matrix_world = Matrix()
        matrix_world.translation = self.location
        if self.container_obj:
            matrix_world.translation.z = self.container_obj.location.z
        obj.matrix_world = matrix_world
        bpy.context.view_layer.update()

        element = bonsai.core.root.assign_class(
            tool.Ifc,
            tool.Collector,
            tool.Root,
            obj=obj,
            ifc_class=ifc_class,
            should_add_representation=False,
        )
        ifcopenshell.api.type.assign_type(
            self.file, related_objects=[element], relating_type=self.relating_type
        )

        bonsai.core.geometry.edit_object_placement(tool.Ifc, tool.Geometry, tool.Surveyor, obj=obj)

        # -- Body: IfcSurfaceCurveSweptAreaSolid
        # The cross-section (IfcRectangleProfileDef) is swept along the user's
        # polyline.  ReferenceSurface = horizontal IfcPlane (normal Z) keeps
        # the rectangle upright regardless of directrix tangent direction.
        unit_scale = self.unit_scale
        builder = ifcopenshell.util.shape_builder.ShapeBuilder(self.file)

        # Build IfcIndexedPolyCurve with explicit IfcLineIndex segments.
        # IFC4+ is required; IFC2X3 is not supported.
        ifc_coords = [(p[0] / unit_scale, p[1] / unit_scale) for p in self.polyline]
        point_list = self.file.createIfcCartesianPointList2D(ifc_coords)
        n = len(ifc_coords)
        segments = [self.file.createIfcLineIndex([i + 1, i + 2]) for i in range(n - 1)]
        # If the user closed the loop the last coord equals the first; adjust the
        # closing segment to reference point index 1 instead of repeating it.
        def _pts_equal(a, b):
            return all(isclose(a[i], b[i], abs_tol=1e-9) for i in range(len(a)))
        if n >= 2 and _pts_equal(ifc_coords[0], ifc_coords[-1]):
            segments[-1] = self.file.createIfcLineIndex([n - 1, 1])
        directrix = self.file.createIfcIndexedPolyCurve(Points=point_list, Segments=segments)
        # directrix_points kept for the Plan/Axis rep below (plain 2-D list)
        directrix_points = ifc_coords

        # Rectangular cross-section: XDim = height, YDim = thickness
        # For IfcSurfaceCurveSweptAreaSolid with a Z-normal reference surface the
        # profile X axis is aligned with the projected surface normal (vertical),
        # so XDim controls height; YDim controls thickness (perpendicular to tangent).
        #
        # Without a Position the profile centroid sits at the directrix, so the wall
        # would extend from -height/2 to +height/2 vertically.  We offset the
        # profile centre by +XDim/2 along the profile X axis (= height direction)
        # so the bottom edge is at the directrix plane (local Z = 0).
        xdim_ifc = self.height / unit_scale
        profile_position = self.file.createIfcAxis2Placement2D(
            Location=self.file.createIfcCartesianPoint([xdim_ifc / 2, 0.0])
        )
        swept_area = self.file.create_entity(
            "IfcRectangleProfileDef",
            ProfileType="AREA",
            Position=profile_position,
            XDim=xdim_ifc,
            YDim=self.thickness / unit_scale,
        )

        # Horizontal reference plane: the XY plane (normal = Z).
        # Its surface normal at every point of the directrix drives the
        # height direction of the swept cross-section.
        reference_surface = builder.plane(location=(0.0, 0.0, 0.0), normal=(0.0, 0.0, 1.0))

        body_item = self.file.create_entity(
            "IfcSurfaceCurveSweptAreaSolid",
            SweptArea=swept_area,
            Directrix=directrix,
            ReferenceSurface=reference_surface,
        )

        representation = builder.get_representation(self.body_context, items=[body_item])
        ifcopenshell.api.geometry.assign_representation(
            self.file, product=element, representation=representation
        )
        bonsai.core.geometry.switch_representation(
            tool.Ifc,
            tool.Geometry,
            obj=obj,
            representation=representation,
        )

        # -- Axis representation (Plan/Axis/GRAPH_VIEW)
        # Stores the 2-D projection of the directrix.  Straight segments become
        # IfcPolyline; arc segments become IfcTrimmedCurve/IfcCircle so that
        # Blender's viewport renders smooth arcs (same technique as the door swing).
        if self.axis_context:
            axis_items = _make_display_axis_items(self.file, directrix)
            axis_rep = self.file.createIfcShapeRepresentation(
                self.axis_context,
                self.axis_context.ContextIdentifier,
                "Curve2D",
                axis_items,
            )
            ifcopenshell.api.geometry.assign_representation(
                self.file, product=element, representation=axis_rep
            )

        # -- Parametric engine tag (used by regeneration handlers)
        pset = ifcopenshell.api.pset.add_pset(self.file, product=element, name="EPset_Parametric")
        ifcopenshell.api.pset.edit_pset(
            self.file, pset=pset, properties={"Engine": WALL_ALONE_ENGINE}
        )

        # Use AXIS2 layer direction: the directrix is the horizontal reference
        # axis, consistent with how regular walls store their material layers.
        material = ifcopenshell.util.element.get_material(element)
        if material and hasattr(material, "LayerSetDirection"):
            material.LayerSetDirection = "AXIS2"

        tool.Blender.select_object(obj)
        return obj

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_layer_thicknesses(self) -> list[float]:
        thicknesses = []
        for rel in self.relating_type.HasAssociations:
            if rel.is_a("IfcRelAssociatesMaterial"):
                material = rel.RelatingMaterial
                if material.is_a("IfcMaterialLayerSet"):
                    thicknesses = [layer.LayerThickness for layer in material.MaterialLayers]
                    break
        return thicknesses

    def _get_ifc_class(self) -> str:
        ifc_classes = ifcopenshell.util.type.get_applicable_entities(
            self.relating_type.is_a(), self.file.schema
        )
        return next(c for c in ifc_classes if "StandardCase" not in c)


# ---------------------------------------------------------------------------
# Creation operator — modal polyline drawing (edit mode via polyline tool)
# ---------------------------------------------------------------------------


class DrawPolylineWallAlone(bpy.types.Operator, PolylineOperator, tool.Ifc.Operator):
    """Draw a WallAlone from an open or closed 2-D polyline axis/directrix.

    Uses the same slab-style polyline interface (Extend, Join, Fillet, 3-point
    arc…).  The polyline is the horizontal centerline of the wall; closure is
    entirely up to the user — confirm with RMB / Enter at any point ≥ 2.
    """

    bl_idname = "bim.draw_polyline_wall_alone"
    bl_label = "Draw Polyline Wall (Alone)"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        if context.space_data.type != "VIEW_3D":
            return False
        ifc = tool.Ifc.get()
        if not ifc or ifc.schema == "IFC2X3":
            cls.poll_message_set("WallAlone requires IFC4 or later.")
            return False
        return True

    def __init__(self, *args, **kwargs):
        bpy.types.Operator.__init__(self, *args, **kwargs)
        PolylineOperator.__init__(self)
        self.relating_type = None
        props = tool.Model.get_model_props()
        relating_type_id = props.relating_type_id
        if relating_type_id:
            self.relating_type = tool.Ifc.get().by_id(int(relating_type_id))

    # ------------------------------------------------------------------
    def _create_wall_from_polyline(self, context: bpy.types.Context):
        """Called on confirmation — generates the WallAlone from the polyline."""
        if not self.relating_type:
            return {"FINISHED"}

        obj = DumbWallAloneGenerator(self.relating_type).generate("POLYLINE")
        if not obj:
            return

        # Apply direction-sense / offset properties (same pattern as slab)
        model_props = tool.Model.get_model_props()
        model = tool.Ifc.get()
        element = tool.Ifc.get_entity(obj)
        material = ifcopenshell.util.element.get_material(element)
        if material and hasattr(material, "id"):
            material_set_usage = model.by_id(material.id())
            if getattr(material_set_usage, "ForLayerSet", False):
                attributes = {
                    "OffsetFromReferenceLine": model_props.offset,
                    "DirectionSense": model_props.direction_sense,
                }
                ifcopenshell.api.material.edit_layer_usage(
                    model, usage=material_set_usage, attributes=attributes
                )

    # ------------------------------------------------------------------
    def modal(self, context, event):
        return IfcStore.execute_ifc_operator(self, context, event, method="MODAL")

    def _modal(self, context, event):
        if not self.relating_type:
            self.report({"WARNING"}, "You need to select a wall type.")
            PolylineDecorator.uninstall()
            tool.Blender.update_viewport()
            return {"FINISHED"}

        PolylineDecorator.update(event, self.tool_state, self.input_ui, self.snapping_points[0])
        tool.Blender.update_viewport()

        self.handle_lock_axis(context, event)

        if event.type in {"MIDDLEMOUSE", "WHEELUPMOUSE", "WHEELDOWNMOUSE"}:
            self.handle_mouse_move(context, event)
            return {"PASS_THROUGH"}

        props = tool.Model.get_model_props()

        # Toggle direction sense (F key) — same convention as slab/wall
        if event.value == "RELEASE" and event.type == "F":
            props.direction_sense = "NEGATIVE" if props.direction_sense == "POSITIVE" else "POSITIVE"
            self.set_offset(context, self.relating_type)

        # Cycle offset type (O key)
        if event.value == "RELEASE" and event.type == "O":
            items = ["TOP", "CENTER", "BOTTOM"]
            index = items.index(props.offset_type_horizontal)
            props.offset_type_horizontal = items[((index + 1) % len(items))]
            self.set_offset(context, self.relating_type)

        custom_instructions = {"Choose Axis": {"icons": True, "keys": ["EVENT_X", "EVENT_Y"]}}
        wall_config = [
            f"Direction: {props.direction_sense}",
            f"Offset Type: {props.offset_type_horizontal}",
            f"Offset Value: {tool.Polyline.format_input_ui_units(props.offset * self.unit_scale)}",
        ]
        self.handle_instructions(context, custom_instructions, wall_config)

        self.handle_mouse_move(context, event, should_round=True)
        self.choose_axis(event)
        self.handle_snap_selection(context, event)

        if (
            not self.tool_state.is_input_on
            and event.value == "RELEASE"
            and event.type in {"RET", "NUMPAD_ENTER", "RIGHTMOUSE"}
        ):
            self._create_wall_from_polyline(context)
            context.workspace.status_text_set(text=None)
            self.tool_state.plane_method = None
            ProductDecorator.uninstall()
            PolylineDecorator.uninstall()
            tool.Polyline.clear_polyline()
            tool.Blender.update_viewport()
            return {"FINISHED"}

        self.handle_keyboard_input(context, event)
        self.handle_inserting_polyline(context, event)

        cancel = self.handle_cancelation(context, event)
        if cancel is not None:
            ProductDecorator.uninstall()
            return cancel

        return {"RUNNING_MODAL"}

    def invoke(self, context, event):
        return IfcStore.execute_ifc_operator(self, context, event, method="INVOKE")

    def _invoke(self, context, event):
        super().invoke(context, event)
        ProductDecorator.install(context)
        self.tool_state.use_default_container = True
        self.tool_state.plane_method = "XY"
        self.set_offset(context, self.relating_type)
        return {"RUNNING_MODAL"}


# ---------------------------------------------------------------------------
# Edit-mode operators — axis/directrix path editing (CAD polyline editor)
# ---------------------------------------------------------------------------
# In edit mode the user modifies the 2-D directrix (horizontal axis path).
# The cross-section geometry (thickness × height) is not changed here.
# The workflow mirrors slab.EnableEditingExtrusionProfile but operates on the
# open-or-closed IfcIndexedPolyCurve stored as the wall's Directrix.
# ---------------------------------------------------------------------------


def _disable_editing_wall_alone_axis(context: bpy.types.Context):
    """Shared teardown logic for leaving WallAlone axis edit mode."""
    ProfileDecorator.uninstall()
    bpy.ops.object.mode_set(mode="OBJECT")

    obj = context.active_object
    element = tool.Ifc.get_entity(obj)
    body = ifcopenshell.util.representation.get_representation(element, "Model", "Body", "MODEL_VIEW")

    bonsai.core.geometry.switch_representation(
        tool.Ifc,
        tool.Geometry,
        obj=obj,
        representation=body,
        apply_openings=False,
    )
    # Re-add Blender boolean modifiers (switch_representation clears them).
    _setup_all_wall_alone_modifiers(obj, element)
    return {"FINISHED"}


class EnableEditingWallAloneAxis(bpy.types.Operator, tool.Ifc.Operator):
    """Enter edit mode to modify the 2-D axis/directrix path of a WallAlone.

    Loads the IfcSurfaceCurveSweptAreaSolid's Directrix into the Blender mesh
    and activates the CAD polyline editor (ProfileDecorator + bim.cad_tool).
    The cross-section rectangle is not affected.

    Mirrors slab.EnableEditingExtrusionProfile but operates on an open or
    closed directrix curve instead of a closed IfcArbitraryClosedProfileDef.
    """

    bl_idname = "bim.enable_editing_wall_alone_axis"
    bl_label = "Edit Wall Alone Axis"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        ifc = tool.Ifc.get()
        if not ifc or ifc.schema == "IFC2X3":
            cls.poll_message_set("WallAlone requires IFC4 or later.")
            return False
        if not context.selected_objects:
            return False
        obj = context.active_object
        if not obj:
            return False
        element = tool.Ifc.get_entity(obj)
        if not element:
            return False
        pset = ifcopenshell.util.element.get_psets(element).get("EPset_Parametric", {})
        return pset.get("Engine") == WALL_ALONE_ENGINE

    def _execute(self, context):
        self.unit_scale = ifcopenshell.util.unit.calculate_unit_scale(tool.Ifc.get())
        obj = context.active_object
        element = tool.Ifc.get_entity(obj)

        body = ifcopenshell.util.representation.get_representation(element, "Model", "Body", "MODEL_VIEW")
        body = ifcopenshell.util.representation.resolve_representation(body)
        body_item = body.Items[0]  # IfcSurfaceCurveSweptAreaSolid

        position = Matrix()
        if body_item.Position:
            position = Matrix(ifcopenshell.util.placement.get_axis2placement(body_item.Position).tolist())
            position.translation *= self.unit_scale

        # Load the directrix curve into the Blender mesh.  import_curve handles
        # IfcIndexedPolyCurve (with IfcArcIndex / IfcLineIndex segments) and
        # sets up IFCARCINDEX vertex groups so the ProfileDecorator can round-
        # trip arc data correctly.
        tool.Model.import_curve(body_item.Directrix, obj=obj, position=position)

        bpy.ops.object.mode_set(mode="EDIT")
        ProfileDecorator.install(
            context,
            exit_edit_mode_callback=lambda: _disable_editing_wall_alone_axis(context),
        )
        if not bpy.app.background:
            tool.Blender.set_viewport_tool("bim.cad_tool")
        return {"FINISHED"}


class DisableEditingWallAloneAxis(bpy.types.Operator, tool.Ifc.Operator):
    """Leave WallAlone axis edit mode without saving changes."""

    bl_idname = "bim.disable_editing_wall_alone_axis"
    bl_label = "Discard Wall Alone Axis Edits"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return bool(context.selected_objects)

    def _execute(self, context):
        return _disable_editing_wall_alone_axis(context)


class EditWallAloneAxis(bpy.types.Operator, tool.Ifc.Operator):
    """Confirm edits made in WallAlone axis edit mode.

    Reads the current mesh edge loop, exports it as an IfcIndexedPolyCurve
    (open or closed — matching whatever the mesh provides), updates the
    Directrix of the IfcSurfaceCurveSweptAreaSolid, and also refreshes the
    Plan/Axis representation.

    Analogous to slab.EditExtrusionProfile but operates on the directrix path
    rather than a closed IfcArbitraryClosedProfileDef.
    """

    bl_idname = "bim.edit_wall_alone_axis"
    bl_label = "Apply Wall Alone Axis Edits"
    bl_options = {"REGISTER", "UNDO"}

    def _execute(self, context):
        self.unit_scale = ifcopenshell.util.unit.calculate_unit_scale(tool.Ifc.get())
        ProfileDecorator.uninstall()
        bpy.ops.object.mode_set(mode="OBJECT")

        obj = context.active_object
        element = tool.Ifc.get_entity(obj)
        ifc_file = tool.Ifc.get()

        body = ifcopenshell.util.representation.get_representation(element, "Model", "Body", "MODEL_VIEW")
        body = ifcopenshell.util.representation.resolve_representation(body)
        body_item = body.Items[0]  # IfcSurfaceCurveSweptAreaSolid

        position = Matrix()
        if body_item.Position:
            position = Matrix(ifcopenshell.util.placement.get_axis2placement(body_item.Position).tolist())
            position.translation *= self.unit_scale

        # Export the edited mesh back to an IfcIndexedPolyCurve.
        # export_curves() uses auto_detect_curves() which reads IFCARCINDEX vertex
        # groups and emits IfcArcIndex / IfcLineIndex segments accordingly.
        new_curves = tool.Model.export_curves(obj, position=position)
        if not new_curves:
            def msg(self, context):
                self.layout.label(text="INVALID AXIS PATH")

            bpy.context.window_manager.popup_menu(msg, title="Error", icon="ERROR")
            ProfileDecorator.install(
                context,
                exit_edit_mode_callback=lambda: _disable_editing_wall_alone_axis(context),
            )
            bpy.ops.object.mode_set(mode="EDIT")
            return

        new_directrix = new_curves[0]
        old_directrix = body_item.Directrix
        body_item.Directrix = new_directrix
        ifcopenshell.util.element.remove_deep2(ifc_file, old_directrix)

        bonsai.core.geometry.switch_representation(
            tool.Ifc,
            tool.Geometry,
            obj=obj,
            representation=body,
            apply_openings=False,
        )
        # Re-add Blender boolean modifiers (switch_representation clears them).
        _setup_all_wall_alone_modifiers(obj, element)

        # Rebuild the Plan/Axis representation from new_directrix using
        # IfcPolyline/IfcTrimmedCurve items so arcs render smoothly.
        axis_context = ifcopenshell.util.representation.get_context(
            ifc_file, "Plan", "Axis", "GRAPH_VIEW"
        )
        if not axis_context:
            return {"FINISHED"}

        axis_items = _make_display_axis_items(ifc_file, new_directrix)
        new_axis_rep = ifc_file.createIfcShapeRepresentation(
            axis_context,
            axis_context.ContextIdentifier,
            "Curve2D",
            axis_items,
        )
        old_axis_rep = ifcopenshell.util.representation.get_representation(
            element, "Plan", "Axis", "GRAPH_VIEW"
        )
        if old_axis_rep:
            for inverse in ifc_file.get_inverse(old_axis_rep):
                ifcopenshell.util.element.replace_attribute(inverse, old_axis_rep, new_axis_rep)
            bonsai.core.geometry.remove_representation(
                tool.Ifc, tool.Geometry, obj=obj, representation=old_axis_rep
            )
        else:
            ifcopenshell.api.geometry.assign_representation(
                ifc_file, product=element, representation=new_axis_rep
            )
        return {"FINISHED"}


