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

import time

import bpy
from bpy.app.handlers import persistent

import bonsai.tool as tool
from bonsai.bim.ifc import IfcStore

from . import operator, prop, ui, workspace

classes = (
    operator.PickStructuralLoads,
    operator.LoadStructuralAnalysisModels,
    operator.DisableStructuralAnalysisModelEditingUI,
    operator.AddStructuralAnalysisModel,
    operator.EditStructuralMemberDetail,
    operator.SelectStructuralModelMember,
    operator.ToggleStructuralModelMemberVisibility,
    operator.ShowStructuralModelMembers,
    operator.GenerateStructuralModel,
    operator.EditStructuralAnalysisModel,
    operator.RemoveStructuralAnalysisModel,
    operator.AssignStructuralAnalysisModel,
    operator.SetCurrentStructuralAnalysisModel,
    operator.UnassignStructuralAnalysisModel,
    operator.EnableEditingStructuralAnalysisModel,
    operator.DisableEditingStructuralAnalysisModel,
    operator.AddStructuralBoundaryCondition,
    operator.EditStructuralBoundaryCondition,
    operator.RemoveStructuralBoundaryCondition,
    operator.EnableEditingStructuralBoundaryCondition,
    operator.DisableEditingStructuralBoundaryCondition,
    operator.AddStructuralMemberConnection,
    operator.EnableEditingStructuralConnectionCondition,
    operator.DisableEditingStructuralConnectionCondition,
    operator.RemoveStructuralConnectionCondition,
    operator.EnableEditingStructuralItemAxis,
    operator.DisableEditingStructuralItemAxis,
    operator.EditStructuralItemAxis,
    operator.EnableEditingStructuralConnectionCS,
    operator.DisableEditingStructuralConnectionCS,
    operator.EditStructuralConnectionCS,
    operator.AssignStructuralLoadCase,
    operator.AddStructuralLoadCase,
    operator.UnassignStructuralLoadCase,
    operator.EditStructuralLoadCase,
    operator.RemoveStructuralLoadCase,
    operator.AddStructuralLoadGroup,
    operator.RemoveStructuralLoadGroup,
    operator.AddStructuralActivity,
    operator.RemoveStructuralActivity,
    operator.ApplyStructuralLoad,
    operator.EditStructuralLoadValues,
    operator.ShowStructuralLoadCase,
    operator.EnableEditingStructuralLoadCase,
    operator.DisableEditingStructuralLoadCase,
    operator.EnableEditingStructuralLoadGroupActivities,
    operator.LoadStructuralLoads,
    operator.DisableStructuralLoadEditingUI,
    operator.AddStructuralLoad,
    operator.EnableEditingStructuralLoad,
    operator.DisableEditingStructuralLoad,
    operator.RemoveStructuralLoad,
    operator.EditStructuralLoad,
    operator.ToggleFilterStructuralLoads,
    operator.LoadBoundaryConditions,
    operator.DisableBoundaryConditionEditingUI,
    operator.AddBoundaryCondition,
    operator.EnableEditingBoundaryCondition,
    operator.DisableEditingBoundaryCondition,
    operator.RemoveBoundaryCondition,
    operator.EditBoundaryCondition,
    operator.ToggleFilterBoundaryConditions,
    prop.StructuralAnalysisModel,
    prop.StructuralMemberDetail,
    prop.StructuralActivity,
    prop.StructuralLoad,
    prop.BoundaryCondition,
    prop.BIMStructuralProperties,
    prop.BIMObjectStructuralProperties,
    ui.BIM_PT_structural_analysis_models,
    ui.BIM_PT_generate_structural_model,
    ui.BIM_UL_structural_model_members,
    ui.BIM_UL_structural_member_details,
    ui.BIM_PT_structural_model_members,
    ui.BIM_PT_structural_member,
    ui.BIM_PT_structural_item_models,
    ui.BIM_PT_structural_item_loads,
    ui.BIM_PT_structural_connection,
    ui.BIM_PT_structural_boundary_conditions,
    ui.BIM_PT_connected_structural_members,
    ui.BIM_UL_structural_analysis_models,
    ui.BIM_UL_structural_activities,
    ui.BIM_PT_show_structural_activities,
    ui.BIM_PT_structural_load_cases,
    ui.BIM_UL_structural_loads,
    ui.BIM_PT_structural_loads,
    ui.BIM_UL_boundary_conditions,
    ui.BIM_PT_boundary_conditions,
    workspace.Hotkey,
)


ignore_source_updates_until = 0.0


def sync_generated_sources():
    if IfcStore.current_transaction:
        return 0.3
    if any(
        op.bl_idname.startswith("TRANSFORM_OT")
        for window in bpy.context.window_manager.windows
        for op in window.modal_operators
    ):
        return 0.3
    if time.monotonic() < ignore_source_updates_until:
        return None
    for model_id in tool.Structural.get_changed_generated_models():
        bpy.ops.bim.generate_structural_model(sync_only=True, structural_model=model_id)
    return None


@persistent
def update_generated_sources(scene, depsgraph):
    if tool.Ifc.get() and time.monotonic() >= ignore_source_updates_until:
        if not bpy.app.timers.is_registered(sync_generated_sources):
            bpy.app.timers.register(sync_generated_sources, first_interval=0.3)


@persistent
def ignore_generated_sources_after_undo(*args):
    global ignore_source_updates_until
    ignore_source_updates_until = time.monotonic() + 1.0
    if bpy.app.timers.is_registered(sync_generated_sources):
        bpy.app.timers.unregister(sync_generated_sources)


def register():
    if not bpy.app.background:
        bpy.utils.register_tool(workspace.StructuralTool, after={"bim.spatial_tool"}, separator=False, group=False)
    bpy.types.Scene.BIMStructuralProperties = bpy.props.PointerProperty(type=prop.BIMStructuralProperties)
    bpy.types.Object.BIMStructuralProperties = bpy.props.PointerProperty(type=prop.BIMObjectStructuralProperties)
    bpy.app.handlers.depsgraph_update_post.append(update_generated_sources)
    bpy.app.handlers.undo_post.append(ignore_generated_sources_after_undo)
    bpy.app.handlers.redo_post.append(ignore_generated_sources_after_undo)


def unregister():
    bpy.app.handlers.depsgraph_update_post.remove(update_generated_sources)
    bpy.app.handlers.undo_post.remove(ignore_generated_sources_after_undo)
    bpy.app.handlers.redo_post.remove(ignore_generated_sources_after_undo)
    if bpy.app.timers.is_registered(sync_generated_sources):
        bpy.app.timers.unregister(sync_generated_sources)
    if not bpy.app.background:
        bpy.utils.unregister_tool(workspace.StructuralTool)
    del bpy.types.Scene.BIMStructuralProperties
    del bpy.types.Object.BIMStructuralProperties
