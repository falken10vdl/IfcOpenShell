# This file was generated with the assistance of an AI coding tool.

from types import SimpleNamespace
from unittest import mock
from unittest.mock import MagicMock

import bpy
import ifcopenshell
import ifcopenshell.api.context
import ifcopenshell.api.geometry
import ifcopenshell.api.group
import ifcopenshell.api.material
import ifcopenshell.api.profile
import ifcopenshell.api.pset
import ifcopenshell.api.root
import ifcopenshell.api.structural
import ifcopenshell.util.structural
import numpy as np
import pytest
from mathutils import Vector

import bonsai.tool as tool
from bonsai.bim.ifc import IfcStore
from bonsai.bim.module.structural.data import LoadGroupDecorationData, StructuralModelMemberData
from bonsai.bim.module.structural.data import refresh as refresh_structural_data
from bonsai.bim.module.structural.decorator import LoadsDecorator
from bonsai.bim.module.structural.operator import PickStructuralLoads
from bonsai.bim.module.structural.ui import (
    BIM_PT_generate_structural_model,
    BIM_PT_structural_model_members,
    BIM_UL_structural_member_details,
)
from test.bim.bootstrap import NewFile, NewIfc


class TestLoadBoundaryConditions(NewFile):
    def test_filtering_duplicate_names(self):
        ifc = ifcopenshell.file(schema="IFC4")
        tool.Ifc.set(ifc)
        ifc.createIfcBoundaryNodeCondition(Name="Fixed")
        ifc.createIfcBoundaryNodeCondition(Name="Fixed")
        ifc.createIfcBoundaryNodeCondition(Name="Pinned")
        props = tool.Structural.get_structural_props()
        props.filtered_boundary_conditions = True
        bpy.ops.bim.load_boundary_conditions()
        assert sorted(c.name for c in props.boundary_conditions) == ["Pinned"]


class TestLoadStructuralLoads(NewFile):
    def test_unused_only(self):
        ifc = ifcopenshell.file(schema="IFC4")
        tool.Ifc.set(ifc)
        point = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcStructuralPointConnection")
        used = ifcopenshell.api.structural.add_structural_load(
            ifc, name="Used", ifc_class="IfcStructuralLoadSingleForce"
        )
        ifcopenshell.api.structural.add_structural_load(ifc, name="Unused", ifc_class="IfcStructuralLoadSingleForce")
        activity = ifcopenshell.api.structural.add_structural_activity(
            ifc, applied_load=used, structural_member=point, ifc_class="IfcStructuralPointAction"
        )
        case = ifcopenshell.api.structural.add_structural_load_case(ifc, name="Case")
        ifcopenshell.api.group.assign_group(ifc, products=[activity], group=case)
        props = tool.Structural.get_structural_props()
        props.show_unused_loads_only = True  # Which lists the loads again.
        assert [load.name for load in props.structural_loads] == ["Unused"]
        props.show_unused_loads_only = False
        assert sorted(load.name for load in props.structural_loads) == ["Unused", "Used"]


class TestShowStructuralLoadCase(NewFile):
    def test_showing_and_hiding_a_load_case(self):
        ifc = ifcopenshell.file(schema="IFC4")
        tool.Ifc.set(ifc)
        model = ifcopenshell.api.structural.add_structural_analysis_model(ifc)
        case = ifcopenshell.api.structural.add_structural_load_case(ifc, name="Case")
        model.LoadedBy = [case]
        LoadGroupDecorationData.is_loaded = False
        props = tool.Structural.get_structural_props()
        props.activity_type = "Action"
        bpy.ops.bim.show_structural_load_case(load_case=case.id())
        assert props.show_loads and props.load_group_to_show == str(case.id())
        # Clicking the open eye of the case shown hides the loads.
        bpy.ops.bim.show_structural_load_case(load_case=case.id())
        assert not props.show_loads


def region(type, x, y, width, height, data=None):
    return SimpleNamespace(type=type, x=x, y=y, width=width, height=height, data=data)


class TestGetViewUnderMouse:
    def get(self, regions, x, y):
        area = SimpleNamespace(type="VIEW_3D", regions=regions)
        context = SimpleNamespace(window=SimpleNamespace(screen=SimpleNamespace(areas=[area])))
        return PickStructuralLoads.get_view_under_mouse(None, context, SimpleNamespace(mouse_x=x, mouse_y=y))

    def test_the_view_of_the_quarter_of_a_quad_view_under_the_mouse(self):
        left, right = region("WINDOW", 0, 0, 100, 100, "left"), region("WINDOW", 100, 0, 100, 100, "right")
        assert self.get([left, right], 150, 50)[1:] == (right, "right")

    def test_not_under_a_sidebar_lying_over_the_view(self):
        view = region("WINDOW", 0, 0, 200, 100, "view")
        sidebar = region("UI", 150, 0, 50, 100)
        assert self.get([view, sidebar], 175, 50) is None
        assert self.get([view, sidebar], 75, 50)[1] is view

    def test_a_hidden_sidebar_takes_nothing(self):
        view = region("WINDOW", 0, 0, 200, 100, "view")
        assert self.get([view, region("UI", 199, 0, 1, 100)], 199, 50)[1] is view


class TestPickLoads:
    def pick(self, x, y):
        LoadsDecorator.shader_info = [{}]
        LoadsDecorator.pickables = [{"tail": (0.0, 0.0, 0.0), "tip": (100.0, 0.0, 0.0), "activity": 7, "info": 0}]
        # Viewed from the front, as if X and Z were the region's x and y.
        project = lambda region, rv3d, point: Vector((point.x, point.z))
        with mock.patch("bonsai.bim.module.structural.decorator.location_3d_to_region_2d", project):
            try:
                return LoadsDecorator.pick(None, None, x, y)
            finally:
                LoadsDecorator.pickables, LoadsDecorator.shader_info = [], []

    def test_an_arrow_within_a_few_pixels(self):
        assert self.pick(60, 5)["activity"] == 7
        assert self.pick(60, 15) is None

    def test_not_at_its_tail_where_its_point_is_selected(self):
        assert self.pick(5, 0) is None


class TestShowStructuralModelMembers(NewIfc):
    @pytest.mark.parametrize("reverse_link", [False, True])
    def test_member_details_include_section_material_load_and_connection(self, reverse_link):
        ifc = tool.Ifc.get()
        model = ifcopenshell.api.structural.add_structural_analysis_model(ifc)
        member = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcStructuralCurveMember", name="Analysis beam")
        ifcopenshell.api.structural.assign_structural_analysis_model(
            ifc, products=[member], structural_analysis_model=model
        )
        source = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcBeam", name="Physical beam")
        if reverse_link:
            ifcopenshell.api.structural.assign_product(ifc, relating_product=source, related_object=member)
        else:
            ifcopenshell.api.structural.assign_product(ifc, relating_product=member, related_object=source)
        profile = ifcopenshell.api.profile.add_parameterized_profile(ifc, ifc_class="IfcRectangleProfileDef")
        profile.ProfileName, profile.XDim, profile.YDim = "Rectangle", 0.2, 0.3
        profile_pset = ifcopenshell.api.pset.add_pset(ifc, product=profile, name="SectionMechanics")
        ifcopenshell.api.pset.edit_pset(ifc, pset=profile_pset, properties={"MomentOfInertiaY": 42.0})
        material = ifcopenshell.api.material.add_material(ifc, name="Steel")
        material_set = ifcopenshell.api.material.add_material_set(ifc, name="Section", set_type="IfcMaterialProfileSet")
        ifcopenshell.api.material.add_profile(ifc, profile_set=material_set, material=material, profile=profile)
        ifcopenshell.api.material.assign_material(
            ifc, products=[source], type="IfcMaterialProfileSet", material=material_set
        )
        material_pset = ifcopenshell.api.pset.add_pset(ifc, product=material, name="Mechanical")
        ifcopenshell.api.pset.edit_pset(
            ifc, pset=material_pset, properties={"ElasticModulus": ifc.createIfcPressureMeasure(210.0)}
        )
        member_pset = ifcopenshell.api.pset.add_pset(ifc, product=member, name="Analysis")
        ifcopenshell.api.pset.edit_pset(ifc, pset=member_pset, properties={"TestValue": 5.0, "Enabled": False})
        quantity_set = ifcopenshell.api.pset.add_qto(ifc, product=member, name="Qto_BeamBaseQuantities")
        ifcopenshell.api.pset.edit_qto(ifc, qto=quantity_set, properties={"Length": 3.0})
        load = ifcopenshell.api.structural.add_structural_load(ifc, name="Wind")
        load.LinearForceX = 12.0
        ifcopenshell.api.structural.add_structural_activity(
            ifc, applied_load=load, structural_member=member, ifc_class="IfcStructuralLinearAction"
        )
        connection = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcStructuralPointConnection", name="Node")
        ifcopenshell.api.structural.add_structural_member_connection(
            ifc, relating_structural_member=member, related_structural_connection=connection
        )
        condition = ifcopenshell.api.structural.add_structural_boundary_condition(
            ifc, connection=connection, name="Pinned"
        )
        condition.TranslationalStiffnessX = ifc.createIfcBoolean(True)
        condition.TranslationalStiffnessY = ifc.createIfcLinearStiffnessMeasure(1000.0)

        StructuralModelMemberData.load(member)
        data = StructuralModelMemberData.data
        assert data["source"] == "Physical beam"
        assert data["profile_source"] == data["material_source"] == "Physical element"
        assert data["profiles"][0]["name"] == "Rectangle"
        assert data["profiles"][0]["values"]["XDim"] == pytest.approx(0.2)
        assert data["materials"][0]["name"] == "Steel"
        assert data["materials"][0]["properties"]["Mechanical"]["ElasticModulus"] == pytest.approx(210)
        assert data["properties"]["Analysis"]["TestValue"] == pytest.approx(5)
        assert data["loads"][0]["name"] == "Wind"
        assert data["loads"][0]["values"]["LinearForceX"] == pytest.approx(12)
        assert data["connections"][0]["name"] == "Node"
        assert data["connections"][0]["conditions"][0]["name"] == "Pinned"
        assert data["connections"][0]["conditions"][0]["values"]["TranslationalStiffnessX"] is True
        tree = StructuralModelMemberData.build_tree(data)
        roots = [row["name"] for row in tree if row["parent"] == -1]
        assert roots == ["Section", "Material", "Member Properties", "Loads", "Connections"]
        value = next(row for row in tree if row["name"] == "TranslationalStiffnessX")
        assert value["value"] == "True"
        assert tree[value["parent"]]["name"] == "Condition"
        assert value["target_kind"] == "BOUNDARY" and value["target_id"] == condition.id()
        modulus = next(row for row in tree if row["name"] == "ElasticModulus")
        assert modulus["target_kind"] == "PROPERTY"
        assert ifc.by_id(modulus["target_id"]).Name == "ElasticModulus"
        tool.Structural.refresh_analysis_model_members()
        tool.Structural.get_structural_props().active_structural_model_member_index = 0
        layout = MagicMock()
        panel = SimpleNamespace(layout=layout)
        BIM_PT_structural_model_members.draw(panel, bpy.context)
        assert layout.template_list.call_count == 2
        props = tool.Structural.get_structural_props()
        rows = props.structural_member_details
        assert {item.name for item in rows} >= {"Rectangle", "Steel", "Wind", "Node"}
        flags, unused_order = BIM_UL_structural_member_details.filter_items(
            SimpleNamespace(bitflag_filter_item=1), bpy.context, props, "structural_member_details"
        )
        assert [row.name for row, flag in zip(rows, flags) if flag] == [
            "Section",
            "Material",
            "Member Properties",
            "Loads",
            "Connections",
        ]
        rows[0].is_expanded = True
        flags, unused_order = BIM_UL_structural_member_details.filter_items(
            SimpleNamespace(bitflag_filter_item=1), bpy.context, props, "structural_member_details"
        )
        assert "Rectangle" in [row.name for row, flag in zip(rows, flags) if flag]
        profile_index = next(index for index, row in enumerate(rows) if row.name == "Rectangle")
        rows[profile_index].is_expanded = True
        flags, unused_order = BIM_UL_structural_member_details.filter_items(
            SimpleNamespace(bitflag_filter_item=1), bpy.context, props, "structural_member_details"
        )
        assert "XDim" in [row.name for row, flag in zip(rows, flags) if flag]
        ifcopenshell.api.pset.edit_pset(ifc, pset=material_pset, properties={"ElasticModulus": 220.0})
        refresh_structural_data()
        assert props.structural_member_details[0].is_expanded
        assert props.structural_member_details[profile_index].is_expanded
        assert next(row.value for row in props.structural_member_details if row.name == "ElasticModulus") == "220"
        modulus_row = next(row for row in props.structural_member_details if row.name == "ElasticModulus")
        bpy.ops.bim.edit_structural_member_detail(detail_key=modulus_row.key, new_value="123.5")
        assert ifcopenshell.util.element.get_pset(material, "Mechanical", "ElasticModulus") == pytest.approx(123.5)
        stiffness_row = next(row for row in props.structural_member_details if row.name == "TranslationalStiffnessX")
        bpy.ops.bim.edit_structural_member_detail(detail_key=stiffness_row.key, new_value="False")
        assert condition.TranslationalStiffnessX.wrappedValue is False
        modulus_row = next(row for row in props.structural_member_details if row.name == "ElasticModulus")
        row_layout = MagicMock()
        BIM_UL_structural_member_details.draw_item(None, bpy.context, row_layout, props, modulus_row, None, props, "")
        row_layout.split.return_value.row.return_value.prop.assert_any_call(modulus_row, "value", text="", emboss=False)
        previous_transaction = IfcStore.history[-1]["key"]
        modulus_row.value = "175.25"
        edit_transaction = IfcStore.history[-1]["key"]
        assert ifcopenshell.util.element.get_pset(material, "Mechanical", "ElasticModulus") == pytest.approx(175.25)
        assert ifc.by_id(modulus_row.target_id).NominalValue.is_a() == "IfcPressureMeasure"
        IfcStore.undo(until_key=previous_transaction)
        assert ifcopenshell.util.element.get_pset(material, "Mechanical", "ElasticModulus") == pytest.approx(123.5)
        IfcStore.redo(until_key=edit_transaction)
        assert ifcopenshell.util.element.get_pset(material, "Mechanical", "ElasticModulus") == pytest.approx(175.25)
        refresh_structural_data()
        stiffness_row = next(row for row in props.structural_member_details if row.name == "TranslationalStiffnessX")
        row_layout = MagicMock()
        BIM_UL_structural_member_details.draw_item(None, bpy.context, row_layout, props, stiffness_row, None, props, "")
        row_layout.split.return_value.row.return_value.prop.assert_any_call(stiffness_row, "boolean_value", text="")
        stiffness_row.boolean_value = True
        assert condition.TranslationalStiffnessX.wrappedValue is True
        spring_row = next(row for row in props.structural_member_details if row.name == "TranslationalStiffnessY")
        spring_row.value = "1250"
        assert condition.TranslationalStiffnessY.is_a() == "IfcLinearStiffnessMeasure"
        assert condition.TranslationalStiffnessY.wrappedValue == pytest.approx(1250)
        enabled_row = next(row for row in props.structural_member_details if row.name == "Enabled")
        enabled_row.boolean_value = True
        assert ifcopenshell.util.element.get_pset(member, "Analysis", "Enabled") is True
        modulus_row = next(row for row in props.structural_member_details if row.name == "ElasticModulus")
        modulus_row.value = "not a number"
        assert ifcopenshell.util.element.get_pset(material, "Mechanical", "ElasticModulus") == pytest.approx(175.25)
        assert modulus_row.value == "175.25"
        load_row = next(row for row in props.structural_member_details if row.name == "LinearForceX")
        load_row.value = "-25.5"
        assert load.LinearForceX == pytest.approx(-25.5)
        quantity_row = next(row for row in props.structural_member_details if row.name == "Length")
        quantity_row.value = "4.25"
        assert ifcopenshell.util.element.get_pset(member, "Qto_BeamBaseQuantities", "Length") == pytest.approx(4.25)
        section_property = next(row for row in props.structural_member_details if row.name == "MomentOfInertiaY")
        section_property.value = "48"
        assert ifcopenshell.util.element.get_pset(profile, "SectionMechanics", "MomentOfInertiaY") == pytest.approx(48)
        profile_row = next(row for row in props.structural_member_details if row.name == "XDim")
        profile_row.value = "0.4"
        assert profile.XDim == pytest.approx(0.4)
        props.structural_member_details[0].is_expanded = False
        flags, unused_order = BIM_UL_structural_member_details.filter_items(
            SimpleNamespace(bitflag_filter_item=1), bpy.context, props, "structural_member_details"
        )
        assert "XDim" not in [row.name for row, flag in zip(props.structural_member_details, flags) if flag]
        layout.operator.assert_any_call("bim.show_structural_model_members", icon="XRAY")
        analysis_material = ifcopenshell.api.material.add_material(ifc, name="Analysis steel")
        ifcopenshell.api.material.assign_material(ifc, products=[member], material=analysis_material)
        StructuralModelMemberData.load(member)
        assert StructuralModelMemberData.data["material_source"] == "Member"
        assert StructuralModelMemberData.data["materials"][0]["name"] == "Analysis steel"

    def test_select_and_toggle_visibility_for_one_member(self):
        ifc = tool.Ifc.get()
        model = ifcopenshell.api.structural.add_structural_analysis_model(ifc)
        member = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcStructuralCurveMember")
        ifcopenshell.api.structural.assign_structural_analysis_model(
            ifc, products=[member], structural_analysis_model=model
        )
        obj = bpy.data.objects.new("Member", bpy.data.meshes.new("Member"))
        bpy.context.scene.collection.objects.link(obj)
        tool.Ifc.link(member, obj)
        assert bpy.ops.bim.toggle_structural_model_member_visibility(member=member.id()) == {"FINISHED"}
        assert obj.hide_get()
        assert bpy.ops.bim.select_structural_model_member(member=member.id()) == {"FINISHED"}
        assert not obj.hide_get() and obj.select_get()
        assert bpy.context.view_layer.objects.active == obj
        assert bpy.ops.bim.toggle_structural_model_member_visibility(member=member.id()) == {"FINISHED"}
        assert bpy.ops.bim.toggle_structural_model_member_visibility(member=member.id()) == {"FINISHED"}
        assert not obj.hide_get()
        collection = bpy.data.collections.new("Hidden member")
        bpy.context.scene.collection.children.link(collection)
        bpy.context.scene.collection.objects.unlink(obj)
        collection.objects.link(obj)
        layer = bpy.context.view_layer.layer_collection.children[collection.name]
        layer.exclude = True
        assert bpy.ops.bim.select_structural_model_member(member=member.id()) == {"FINISHED"}
        assert not layer.exclude and obj.visible_get() and obj.select_get()
        other_model = ifcopenshell.api.structural.add_structural_analysis_model(ifc)
        tool.Structural.set_current_structural_analysis_model(other_model)
        assert bpy.ops.bim.select_structural_model_member(member=member.id()) == {"CANCELLED"}

    def test_member_list_tracks_current_model_and_selection(self):
        ifc = tool.Ifc.get()
        model = ifcopenshell.api.structural.add_structural_analysis_model(ifc)
        other_model = ifcopenshell.api.structural.add_structural_analysis_model(ifc)
        member = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcStructuralCurveMember", name="Member")
        point = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcStructuralPointConnection")
        ifcopenshell.api.structural.assign_structural_analysis_model(
            ifc, products=[member, point], structural_analysis_model=model
        )
        tool.Structural.set_current_structural_analysis_model(model)
        props = tool.Structural.get_structural_props()
        assert [item.ifc_definition_id for item in props.structural_model_members] == [member.id()]
        props.active_structural_model_member_index = 0
        assert props.structural_member_details
        tool.Structural.refresh_analysis_model_members()
        assert props.active_structural_model_member_index == 0
        tool.Structural.set_current_structural_analysis_model(other_model)
        assert not props.structural_model_members
        assert not props.structural_member_details
        assert props.active_structural_model_member_index == -1

    def test_selects_current_model_members_and_toggles_xray(self):
        ifc = tool.Ifc.get()
        model = ifcopenshell.api.structural.add_structural_analysis_model(ifc)
        other_model = ifcopenshell.api.structural.add_structural_analysis_model(ifc)
        tool.Structural.set_current_structural_analysis_model(model)
        objects = []
        for structural_model in (model, other_model):
            member = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcStructuralCurveMember")
            ifcopenshell.api.structural.assign_structural_analysis_model(
                ifc, products=[member], structural_analysis_model=structural_model
            )
            obj = bpy.data.objects.new("Member", bpy.data.meshes.new("Member"))
            bpy.context.scene.collection.objects.link(obj)
            tool.Ifc.link(member, obj)
            objects.append(obj)
        collection = bpy.data.collections.new("Hidden structural members")
        bpy.context.scene.collection.children.link(collection)
        bpy.context.scene.collection.objects.unlink(objects[0])
        collection.objects.link(objects[0])
        bpy.context.view_layer.layer_collection.children[collection.name].hide_viewport = True
        objects[0].hide_set(True)
        objects[1].select_set(True)
        area = next(area for area in bpy.context.screen.areas if area.type == "VIEW_3D")
        xray = area.spaces.active.shading.show_xray
        assert bpy.ops.bim.show_structural_model_members() == {"FINISHED"}
        assert area.spaces.active.shading.show_xray != xray
        assert objects[0].select_get() and not objects[0].hide_get()
        assert objects[0].visible_get()
        assert not objects[1].select_get()
        assert bpy.context.view_layer.objects.active == objects[0]


class TestGenerateStructuralModel(NewIfc):
    def test_panel_has_one_generate_button(self):
        layout = MagicMock()
        BIM_PT_generate_structural_model.draw(SimpleNamespace(layout=layout), bpy.context)
        layout.operator.assert_called_once_with("bim.generate_structural_model", icon="MOD_SIMPLIFY")

    @pytest.mark.parametrize("source_count", [0, 2])
    def test_missing_or_ambiguous_source_preserves_member(self, source_count, capsys):
        ifc = tool.Ifc.get()
        model = ifcopenshell.api.structural.add_structural_analysis_model(ifc)
        member = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcStructuralCurveMember")
        ifcopenshell.api.structural.assign_structural_analysis_model(
            ifc, products=[member], structural_analysis_model=model
        )
        link = tool.Structural.get_structural_props().generation_links.add()
        link.model_guid, link.member_guid = model.GlobalId, member.GlobalId
        for _ in range(source_count):
            source = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcColumn")
            ifcopenshell.api.structural.assign_product(ifc, relating_product=member, related_object=source)

        assert tool.Structural.get_changed_generated_models() == {model.id()}
        changes = tool.Structural.get_member_changes(model)
        assert [change["reason"] for change in changes] == [
            "MISSING_SOURCE" if source_count == 0 else "MULTIPLE_SOURCES"
        ]
        assert bpy.ops.bim.update_structural_model(structural_model=model.id()) == {"FINISHED"}
        assert "missing or ambiguous source relationships" in capsys.readouterr().out
        assert member in ifc.by_type("IfcStructuralCurveMember")

    @pytest.mark.parametrize("reverse_link", [False, True])
    @pytest.mark.parametrize("scene_tolerance", [None, 0.2])
    def test_explicit_refresh_of_linked_member(self, reverse_link, scene_tolerance, capsys):
        ifc = tool.Ifc.get()
        model_context = ifcopenshell.util.representation.get_context(ifc, "Model")
        body = ifcopenshell.api.context.add_context(
            ifc, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=model_context
        )
        profile = ifcopenshell.api.profile.add_parameterized_profile(ifc, ifc_class="IfcRectangleProfileDef")
        profile.XDim, profile.YDim = 0.2, 0.3
        model = ifcopenshell.api.structural.add_structural_analysis_model(ifc)
        source = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcColumn", name="Column")
        representation = ifcopenshell.api.geometry.add_profile_representation(
            ifc, context=body, profile=profile, depth=3.1
        )
        ifcopenshell.api.geometry.assign_representation(ifc, product=source, representation=representation)
        obj = bpy.data.objects.new("Column", bpy.data.meshes.new("Column"))
        bpy.context.scene.collection.objects.link(obj)
        tool.Ifc.link(source, obj)
        obj.location.z = 0.13
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.context.view_layer.update()
        bpy.ops.bim.generate_structural_model()
        member = ifc.by_type("IfcStructuralCurveMember")[0]
        assert not tool.Structural.get_changed_generated_models()
        obj.location.x = 0.00001
        bpy.context.view_layer.update()
        assert tool.Structural.get_changed_generated_models() == {model.id()}
        obj.location.x = 0
        bpy.context.view_layer.update()
        if reverse_link:
            relation = next(rel for rel in source.HasAssignments if rel.is_a("IfcRelAssignsToProduct"))
            relation.RelatingProduct = source
            relation.RelatedObjects = [member]
        nodes = ifc.by_type("IfcStructuralPointConnection")
        assert all(
            not ifcopenshell.util.element.get_pset(item, "BBIM_StructuralGeneration")
            for item in [model, member, *nodes]
        )
        for item, properties in (
            (model, {"MergeTolerance": 0.1}),
            (member, {"Source": source.GlobalId, "SourceAxis": "old", "Keep": "value"}),
            (nodes[0], {"Generated": True}),
        ):
            pset = ifcopenshell.api.pset.add_pset(ifc, product=item, name="BBIM_StructuralGeneration")
            ifcopenshell.api.pset.edit_pset(ifc, pset=pset, properties=properties)
        props = tool.Structural.get_structural_props()
        if scene_tolerance is None:
            props.property_unset("generation_merge_tolerance")
        else:
            props.generation_merge_tolerance = scene_tolerance
        obj.location.x = 2
        bpy.context.view_layer.update()
        assert tool.Structural.get_changed_generated_models() == {model.id()}
        assert tool.Ifc.get_object(member).location.x == pytest.approx(0)
        ifc_before_check = ifc.to_string()
        history_before_check = len(IfcStore.history)
        changes = tool.Structural.get_member_changes(model)
        assert len(changes) == 1
        assert changes[0]["member"] == member and changes[0]["source"] == source
        assert [point["endpoint"] for point in changes[0]["points"]] == ["Start", "End"]
        assert changes[0]["points"][0]["member_point"][0] == pytest.approx(0)
        assert changes[0]["points"][0]["source_point"][0] == pytest.approx(2)
        assert changes[0]["points"][0]["distance"] == pytest.approx(2)
        assert changes[0]["tolerance"] >= props.generation_merge_tolerance
        layout = MagicMock()
        BIM_PT_generate_structural_model.draw(SimpleNamespace(layout=layout), bpy.context)
        layout.label.assert_called_with(text="Linked members have changed or missing sources", icon="ERROR")
        layout.operator.assert_any_call("bim.update_structural_model", icon="FILE_REFRESH")
        layout.box.return_value.label.assert_any_call(
            text=f"Difference: 2 m; tolerance: {changes[0]['tolerance']:.6g} m"
        )
        assert ifc.to_string() == ifc_before_check
        assert len(IfcStore.history) == history_before_check
        previous_transaction = IfcStore.history[-1]["key"]
        assert bpy.ops.bim.update_structural_model(structural_model=model.id()) == {"FINISHED"}
        assert len(IfcStore.history) == history_before_check + 1
        update_transaction = IfcStore.history[-1]["key"]
        ifc_after_update = ifc.to_string()
        IfcStore.undo(until_key=previous_transaction)
        assert ifc.to_string() == ifc_before_check
        IfcStore.redo(until_key=update_transaction)
        assert ifc.to_string() == ifc_after_update
        assert tool.Ifc.get_object(member).location.x == pytest.approx(2)
        assert not tool.Structural.get_changed_generated_models()
        assert not ifcopenshell.util.element.get_pset(model, "BBIM_StructuralGeneration")
        assert props.generation_merge_tolerance == pytest.approx(0.1 if scene_tolerance is None else scene_tolerance)
        assert not ifcopenshell.util.element.get_pset(nodes[0], "BBIM_StructuralGeneration")
        assert ifcopenshell.util.element.get_pset(member, "BBIM_StructuralGeneration")["Keep"] == "value"
        assert set(ifcopenshell.util.element.get_pset(member, "BBIM_StructuralGeneration")) == {"id", "Keep"}
        member_obj = tool.Ifc.get_object(member)
        tool.Structural.get_structural_props().generation_merge_tolerance = 0.1
        member_obj.data.vertices[1].co.x = 0.3
        bpy.context.view_layer.update()
        changes = tool.Structural.get_member_changes(model)
        assert [point["endpoint"] for point in changes[0]["points"]] == ["End"]
        assert changes[0]["points"][0]["distance"] == pytest.approx(0.3)
        member_obj.data.vertices[1].co.x = 0
        member_obj.location.x = 2.05
        bpy.context.view_layer.update()
        assert not tool.Structural.get_changed_generated_models()
        member_obj.location.x = 2.15
        bpy.context.view_layer.update()
        assert tool.Structural.get_changed_generated_models() == {model.id()}
        assert member_obj.location.x == pytest.approx(2.15)
        bpy.ops.bim.update_structural_model(structural_model=model.id())
        assert member_obj.location.x == pytest.approx(2)
        tool.Geometry.delete_ifc_object(obj)
        assert tool.Structural.get_changed_generated_models() == {model.id()}
        bpy.ops.bim.generate_structural_model(sync_only=True)
        assert "missing or ambiguous source relationships" in capsys.readouterr().out
        assert member in ifc.by_type("IfcStructuralCurveMember")
        assert len(ifc.by_type("IfcStructuralPointConnection")) == 2

    @pytest.mark.parametrize("tolerance,point_count", [(0.0, 4), (0.1, 3)])
    @pytest.mark.parametrize("reverse_link", [False, True])
    def test_selected_columns_are_connected_and_assigned(self, tolerance, point_count, reverse_link):
        ifc = tool.Ifc.get()
        model_context = ifcopenshell.util.representation.get_context(ifc, "Model")
        body = ifcopenshell.api.context.add_context(
            ifc, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=model_context
        )
        profile = ifcopenshell.api.profile.add_parameterized_profile(ifc, ifc_class="IfcRectangleProfileDef")
        profile.XDim, profile.YDim = 0.2, 0.3
        model = ifcopenshell.api.structural.add_structural_analysis_model(ifc)
        tool.Structural.get_structural_props().generation_merge_tolerance = tolerance
        sources = []
        for index, height in enumerate((0.0, 3.05 if tolerance else 3.0)):
            source = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcColumn", name=f"Column {index}")
            representation = ifcopenshell.api.geometry.add_profile_representation(
                ifc, context=body, profile=profile, depth=3
            )
            ifcopenshell.api.geometry.assign_representation(ifc, product=source, representation=representation)
            obj = bpy.data.objects.new(source.Name, bpy.data.meshes.new(source.Name))
            bpy.context.scene.collection.objects.link(obj)
            tool.Ifc.link(source, obj)
            obj.location.z = height
            obj.select_set(True)
            sources.append(source)
        bpy.context.view_layer.objects.active = obj
        bpy.context.view_layer.update()

        assert bpy.ops.bim.generate_structural_model() == {"FINISHED"}
        members = ifc.by_type("IfcStructuralCurveMember")
        points = ifc.by_type("IfcStructuralPointConnection")
        assert len(members) == 2
        assert len(points) == point_count
        assert len(ifc.by_type("IfcRelConnectsStructuralMember")) == 4
        assert all(member.Axis for member in members)
        assert all(
            ifcopenshell.util.representation.get_representation(item, "Model", "Reference", "GRAPH_VIEW")
            for item in members + points
        )
        assert all(any(rel.RelatingProduct in members for rel in source.HasAssignments) for source in sources)
        assert all(
            not ifcopenshell.util.element.get_pset(item, "BBIM_StructuralGeneration")
            for item in [model, *members, *points]
        )
        assert not tool.Structural.get_changed_generated_models()
        if reverse_link:
            for source in sources:
                relation = next(rel for rel in source.HasAssignments if rel.is_a("IfcRelAssignsToProduct"))
                member = relation.RelatingProduct
                relation.RelatingProduct = source
                relation.RelatedObjects = [member]
        source_obj = tool.Ifc.get_object(sources[0])
        source_obj.location.x = 1
        bpy.context.view_layer.update()
        changes = tool.Structural.get_member_changes(model)
        assert len(changes) == 1 and changes[0]["source"] == sources[0]
        source_obj.location.x = 0
        bpy.context.view_layer.update()
        assert set(model.IsGroupedBy[0].RelatedObjects) == set(members + points)
        assert all(tool.Ifc.get_object(item) for item in members + points)
        bpy.ops.bim.generate_structural_model()
        assert len(ifc.by_type("IfcStructuralCurveMember")) == 2
        original_positions = {member.id(): tool.Ifc.get_object(member).location.copy() for member in members}
        for source in sources:
            tool.Ifc.get_object(source).location.x += 2
        bpy.context.view_layer.update()
        assert tool.Structural.get_changed_generated_models() == {model.id()}
        bpy.ops.object.select_all(action="DESELECT")
        bpy.ops.bim.generate_structural_model(sync_only=True)
        assert not tool.Structural.get_changed_generated_models()
        for member in members:
            assert tool.Ifc.get_object(member).location.x == pytest.approx(original_positions[member.id()].x + 2)
        assert len(ifc.by_type("IfcStructuralPointConnection")) == point_count
        source = sources[1]
        extrusion = ifcopenshell.util.representation.get_representation(source, "Model", "Body", "MODEL_VIEW").Items[0]
        extrusion.Depth += 1 / ifcopenshell.util.unit.calculate_unit_scale(ifc)
        bpy.ops.bim.generate_structural_model(sync_only=True)
        member = ifcopenshell.util.structural.get_structural_members(source)[0]
        assert tool.Ifc.get_object(member).data.vertices[1].co.length == pytest.approx(4, abs=0.1)
        shared_node = next(
            (node for node in ifc.by_type("IfcStructuralPointConnection") if len(node.ConnectsStructuralMembers) == 2),
            None,
        )
        shared_condition = (
            ifcopenshell.api.structural.add_structural_boundary_condition(ifc, connection=shared_node)
            if shared_node
            else None
        )
        tool.Ifc.get_object(sources[0]).location.x += 1
        tool.Ifc.get_object(sources[0]).rotation_euler.y = 1.5707963267948966
        bpy.context.view_layer.update()
        bpy.ops.bim.generate_structural_model(sync_only=True)
        assert len(ifc.by_type("IfcStructuralPointConnection")) == 4
        assert len(ifc.by_type("IfcRelConnectsStructuralMember")) == 4
        if shared_condition:
            assert shared_node.AppliedCondition == shared_condition

        rotated_member = ifcopenshell.util.structural.get_structural_members(sources[0])[0]
        direction = np.array(tool.Ifc.get_object(rotated_member).data.vertices[1].co)
        assert np.dot(direction, rotated_member.Axis.DirectionRatios) == pytest.approx(0, abs=1e-6)
        tool.Ifc.get_object(sources[0]).location.x -= 1
        tool.Ifc.get_object(sources[0]).rotation_euler.y = 0
        bpy.context.view_layer.update()
        bpy.ops.bim.generate_structural_model(sync_only=True)
        assert len(ifc.by_type("IfcStructuralPointConnection")) == (3 if tolerance else 4)
        new_source = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcColumn", name="Later Column")
        representation = ifcopenshell.api.geometry.add_profile_representation(
            ifc, context=body, profile=profile, depth=3
        )
        ifcopenshell.api.geometry.assign_representation(ifc, product=new_source, representation=representation)
        obj = bpy.data.objects.new(new_source.Name, bpy.data.meshes.new(new_source.Name))
        bpy.context.scene.collection.objects.link(obj)
        tool.Ifc.link(new_source, obj)
        obj.location = (2, 0, 7.05 if tolerance else 7.0)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.context.view_layer.update()
        tool.Structural.get_structural_props().generation_merge_tolerance = tolerance
        bpy.ops.bim.generate_structural_model()
        assert len(ifc.by_type("IfcStructuralCurveMember")) == 3
        assert len(ifc.by_type("IfcStructuralPointConnection")) == (4 if tolerance else 6)
        removed_member = ifcopenshell.util.structural.get_structural_members(sources[0])[0]
        load = ifcopenshell.api.structural.add_structural_load(ifc)
        activity = ifcopenshell.api.structural.add_structural_activity(
            ifc, applied_load=load, structural_member=removed_member, ifc_class="IfcStructuralLinearAction"
        )
        activity_id = activity.id()
        node = next(
            rel.RelatedStructuralConnection
            for rel in removed_member.ConnectedBy
            if len(rel.RelatedStructuralConnection.ConnectsStructuralMembers) == 1
        )
        condition = ifcopenshell.api.structural.add_structural_boundary_condition(ifc, connection=node)
        condition_id = condition.id()
        tool.Geometry.delete_ifc_object(tool.Ifc.get_object(sources[0]))
        assert tool.Structural.get_changed_generated_models() == {model.id()}
        bpy.ops.bim.generate_structural_model(sync_only=True)
        assert removed_member in ifc.by_type("IfcStructuralCurveMember")
        assert len(ifc.by_type("IfcStructuralPointConnection")) == (4 if tolerance else 6)
        assert len(ifc.by_type("IfcRelConnectsStructuralMember")) == 6
        assert any(item.id() == activity_id for item in ifc.by_type("IfcStructuralActivity"))
        assert any(item.id() == condition_id for item in ifc.by_type("IfcBoundaryCondition"))
        if shared_condition:
            assert shared_node.AppliedCondition == shared_condition

    def test_generation_scene_state_survives_blend_save(self, tmp_path):
        props = tool.Structural.get_structural_props()
        props.generation_merge_tolerance = 0.25
        link = props.generation_links.add()
        link.model_guid, link.member_guid = "model-guid", "member-guid"
        path = str(tmp_path / "structural.blend")
        bpy.ops.wm.save_as_mainfile(filepath=path)
        props.generation_links.clear()
        props.generation_merge_tolerance = 0
        bpy.ops.wm.open_mainfile(filepath=path)
        props = tool.Structural.get_structural_props()
        assert props.generation_merge_tolerance == pytest.approx(0.25)
        assert [(link.model_guid, link.member_guid) for link in props.generation_links] == [
            ("model-guid", "member-guid")
        ]
