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

# This file was generated with the assistance of an AI coding tool.

"""Bonsai Attribute bexpeng integration helpers.

Extracted from bonsai.bim.operator to break the circular import that arose
when material/operator.py and attribute/operator.py imported engine helpers
from operator.py while operator.py was itself still being initialised (it
imports from ui.py which transitively imports material and attribute modules).

Keeping this machinery in a leaf module with no dependency on ui.py resolves
the cycle.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Union

import bpy
import ifcopenshell.util.element
import bonsai.tool as tool
from bonsai.bim.plain_prop_expression import _is_bexpeng_enabled, _is_bexpeng_available

if TYPE_CHECKING:
    from bonsai.bim.prop import Attribute

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level store: data_path -> (param_name, callback)
# ---------------------------------------------------------------------------
_attr_engine_subscriptions: dict[str, tuple[str, object]] = {}


def _apply_material_set_item_value_to_ifc(
    material_set_item_id: int,
    attribute_name: str,
    value: object,
    data_type: str,
    special_type: str,
) -> None:
    """Apply a propagated shared-parameter value directly to IFC material set item."""
    if not material_set_item_id or not attribute_name:
        _log.debug(
            "[bim.shared_parameter] skip IFC apply: invalid target item_id=%r attribute=%r",
            material_set_item_id,
            attribute_name,
        )
        return

    ifc_file = tool.Ifc.get()
    item = ifc_file.by_id(material_set_item_id)
    if item is None or not hasattr(item, attribute_name):
        _log.debug(
            "[bim.shared_parameter] skip IFC apply: target not found or missing attribute item_id=%r attribute=%r",
            material_set_item_id,
            attribute_name,
        )
        return

    converted_value: object
    if data_type == "integer":
        converted_value = int(round(float(value)))  # type: ignore[arg-type]
    elif data_type == "float":
        float_value = float(value)  # type: ignore[arg-type]
        if special_type == "LENGTH":
            try:
                import ifcopenshell.util.unit

                si_conversion = ifcopenshell.util.unit.calculate_unit_scale(ifc_file)
                converted_value = float_value / si_conversion if si_conversion else float_value
            except Exception:
                converted_value = float_value
        else:
            converted_value = float_value
    elif data_type in ("string", "label"):
        converted_value = str(value)
    else:
        return

    try:
        setattr(item, attribute_name, converted_value)
        _log.debug(
            "[bim.shared_parameter] IFC apply item_id=%r attribute=%r value=%r",
            material_set_item_id,
            attribute_name,
            converted_value,
        )
    except Exception:
        _log.debug(
            "[bim.shared_parameter] IFC apply failed item_id=%r attribute=%r value=%r",
            material_set_item_id,
            attribute_name,
            converted_value,
            exc_info=True,
        )
        return

    # Keep generated geometry in sync for common layer-driven elements.
    try:
        if item.is_a("IfcMaterialLayer"):
            from bonsai.bim.module.model import slab, wall

            slab.DumbSlabPlaner().regenerate_from_layer(item)
            wall.DumbWallPlaner().regenerate_from_layer(item)
    except Exception:
        pass

    # Invalidate material UI caches and repaint so read-only panel values
    # reflect shared-parameter updates immediately.
    try:
        from bonsai.bim.module.material import data as material_data

        material_data.refresh()
    except Exception:
        pass
    try:
        import bonsai.bim.handler

        bonsai.bim.handler.refresh_ui_data()
    except Exception:
        pass


def _resolve_material_set_item_id_from_bindings(
    owner_obj: bpy.types.Object,
    param_name: str,
    attribute_name: str,
) -> int:
    """Resolve set-item id from persisted material binding map.

    Used when `active_material_set_item_id` is 0 (outside edit mode).
    """
    try:
        element = tool.Ifc.get_entity(owner_obj)
    except Exception:
        return 0
    element_key = (getattr(element, "GlobalId", "") or "").strip()
    if not element_key:
        return 0

    raw = getattr(tool.Project.get_project_props(), "material_set_item_expression_bindings_json", "") or "{}"
    try:
        bindings = json.loads(raw)
    except Exception:
        return 0
    if not isinstance(bindings, dict):
        return 0

    element_bindings = bindings.get(element_key, {})
    if not isinstance(element_bindings, dict):
        return 0

    def _resolve_material_set_item_id_from_semantic_key(semantic_key: str) -> int:
        ifc_file = tool.Ifc.get()
        parts = semantic_key.split("|", 2)
        if len(parts) != 3:
            return 0
        item_class, set_name, raw_index = parts
        try:
            index = int(raw_index)
        except Exception:
            return 0

        if item_class == "IfcMaterialLayer":
            for layer_set in ifc_file.by_type("IfcMaterialLayerSet"):
                if (layer_set.LayerSetName or "") != set_name:
                    continue
                layers = list(layer_set.MaterialLayers or [])
                if 0 <= index < len(layers) and layers[index]:
                    return int(layers[index].id())

        if item_class == "IfcMaterialProfile":
            for profile_set in ifc_file.by_type("IfcMaterialProfileSet"):
                if (profile_set.Name or "") != set_name:
                    continue
                profiles = list(profile_set.MaterialProfiles or [])
                if 0 <= index < len(profiles) and profiles[index]:
                    return int(profiles[index].id())

        if item_class == "IfcMaterialConstituent":
            for constituent_set in ifc_file.by_type("IfcMaterialConstituentSet"):
                if (constituent_set.Name or "") != set_name:
                    continue
                constituents = list(constituent_set.MaterialConstituents or [])
                if 0 <= index < len(constituents) and constituents[index]:
                    return int(constituents[index].id())

        return 0

    for set_item_id, attr_map in element_bindings.items():
        if not isinstance(attr_map, dict):
            continue
        data = attr_map.get(attribute_name)
        if not isinstance(data, dict):
            continue
        if (data.get("shared_parameter_name") or "") == param_name:
            if str(set_item_id).startswith("key:"):
                return _resolve_material_set_item_id_from_semantic_key(str(set_item_id)[4:])
            try:
                return int(set_item_id)
            except Exception:
                continue
    return 0


def _sync_attribute_expression_to_engine(
    attr: "Attribute", data_path: str, *, apply_local_expression: bool = True
) -> None:
    """Register / update a Bonsai Attribute in the bexpeng engine."""
    if not _is_bexpeng_available():
        return
    import bexpeng

    engine = bexpeng.get_engine()
    param_name = (getattr(attr, "shared_parameter_name", "") or "").strip()
    if not param_name:
        return

    expr_str = (getattr(attr, "shared_parameter_expression", "") or "").strip()
    if not apply_local_expression:
        expr_str = ""
    if expr_str.startswith("="):
        expr_str = expr_str[1:].strip()

    # Current numeric value for initial registration.
    try:
        raw = attr.get_value()
        current_value = float(raw) if isinstance(raw, (int, float)) else 0.0
    except Exception:
        current_value = 0.0

    fallback_set_item_id = 0
    fallback_attr_name = attr.name
    fallback_data_type = attr.data_type
    fallback_special_type = attr.special_type
    try:
        owner_obj = attr.id_data
        mprops = getattr(owner_obj, "BIMObjectMaterialProperties", None)
        if mprops is not None:
            fallback_set_item_id = int(getattr(mprops, "active_material_set_item_id", 0) or 0)
    except Exception:
        fallback_set_item_id = 0

    # Subscribe a callback (replace previous one for this data_path).
    # Keyed by data_path so multiple attributes sharing the same param_name
    # each keep their own subscription and the ref count is correct.
    # Important: subscribe before expression registration so we do not miss the
    # initial solve notification (e.g. constant expressions like '=0.2').
    old = _attr_engine_subscriptions.get(data_path)
    if old is not None:
        engine.unsubscribe(old[0], old[1])

    def _on_value_changed(name: str) -> None:
        value = engine.get_value(name)
        if value is None:
            return
        float_val: float = 0.0
        try:
            float_val = float(value)
        except Exception:
            # Non-numeric value: only continue for string/label attributes.
            if not isinstance(value, str):
                return

        _log.debug(
            "[bim.shared_parameter] callback name=%r value=%r data_path=%r",
            name,
            value,
            data_path,
        )

        try:
            resolved = eval(data_path)  # noqa: S307 – trusted internal path
        except Exception:
            _log.debug(
                "[bim.shared_parameter] data_path unresolved, fallback to IFC item_id=%r attr=%r",
                fallback_set_item_id,
                fallback_attr_name,
            )
            _apply_material_set_item_value_to_ifc(
                fallback_set_item_id,
                fallback_attr_name,
                value,
                fallback_data_type,
                fallback_special_type,
            )
            return
        try:
            # Parameter bindings must update the attribute value even when this
            # attribute is not expression-driven locally (param_name-only mode).
            if resolved.data_type == "integer":
                resolved.int_value = int(round(float_val))
            elif resolved.data_type == "float":
                resolved.float_value = float_val
            elif resolved.data_type in ("string", "label"):
                resolved.string_value = str(value)

            # Keep binding metadata aligned with current engine expression,
            # so restored UI does not show stale expressions.
            try:
                current_expr = engine.get_expression(name)
                # In binding-only mode, preserve previously restored expression text
                # if engine doesn't currently expose one.
                if apply_local_expression:
                    resolved.shared_parameter_expression = current_expr or ""
                elif current_expr:
                    resolved.shared_parameter_expression = current_expr
            except Exception:
                pass

            _log.debug(
                "[bim.shared_parameter] UI apply attr=%r data_type=%r special_type=%r value=%r",
                resolved.name,
                resolved.data_type,
                resolved.special_type,
                value,
            )
            # Also push to IFC so updates work even outside material set item edit mode.
            current_set_item_id = fallback_set_item_id
            try:
                owner_obj = resolved.id_data
                mprops = getattr(owner_obj, "BIMObjectMaterialProperties", None)
                if mprops is not None:
                    current_set_item_id = int(getattr(mprops, "active_material_set_item_id", 0) or 0)
                    if not current_set_item_id:
                        current_set_item_id = _resolve_material_set_item_id_from_bindings(
                            owner_obj,
                            name,
                            resolved.name,
                        )
            except Exception:
                pass
            _apply_material_set_item_value_to_ifc(
                current_set_item_id,
                resolved.name,
                value,
                resolved.data_type,
                resolved.special_type,
            )

            # Persist metadata updates (e.g. refreshed shared expression text).
            _persist_material_set_item_binding_if_needed(resolved, data_path)
        except Exception:
            pass

    engine.subscribe(param_name, _on_value_changed)
    _attr_engine_subscriptions[data_path] = (param_name, _on_value_changed)

    if expr_str:
        # Local expression mode: set_parameter creates/updates and notifies subscribers.
        try:
            engine.set_parameter(param_name, expr_str)
        except Exception as exc:
            # Show as a Blender report; caller can decide what to do.
            raise RuntimeError(str(exc)) from exc
    elif engine.get_expression(param_name) is None:
        # Shared-parameter mode: seed with current value only if not yet in engine.
        engine.set_parameter(param_name, str(current_value))

    # Pull once in case the backend didn't emit a callback (e.g. value unchanged).
    # This also guarantees immediate UI sync after closing the popup.
    if engine.get_value(param_name) is not None:
        _on_value_changed(param_name)


def _clear_attribute_expression_from_engine(data_path: str) -> None:
    """Drop Bonsai's local subscription for the binding at *data_path*.

    Parameter/expression lifetime in the engine is managed by bexpeng itself
    (via its own reference counting).  Bonsai only removes its callback.
    """
    if not data_path or not _is_bexpeng_available():
        return

    import bexpeng

    engine = bexpeng.get_engine()

    old = _attr_engine_subscriptions.pop(data_path, None)
    if old is not None:
        try:
            engine.unsubscribe(old[0], old[1])
        except Exception:
            pass


def _persist_material_set_item_binding_if_needed(attr: "Attribute", data_path: str = "") -> None:
    """Persist expression binding for an attribute immediately.

    Handles BIMAttributeProperties entity attributes as well as material set
    item/usage attributes so bindings survive closing/reopening edit UIs.
    """
    owner = attr.id_data
    element = tool.Ifc.get_entity(owner)
    if element is None:
        return
    element_key = (element.GlobalId or "").strip()
    if not element_key:
        return

    param_name = (getattr(attr, "shared_parameter_name", "") or "").strip()
    expression = (getattr(attr, "shared_parameter_expression", "") or "").strip()

    def _persist_bindings(json_attr_name: str, owner_key: str, override_key: "Union[str, None]" = None) -> None:
        ek = override_key if override_key is not None else element_key
        bindings_raw = getattr(tool.Project.get_project_props(), json_attr_name, "") or "{}"
        try:
            bindings = json.loads(bindings_raw)
            if not isinstance(bindings, dict):
                bindings = {}
        except json.JSONDecodeError:
            bindings = {}

        element_bindings = bindings.get(ek)
        if not isinstance(element_bindings, dict):
            element_bindings = {}

        owner_bindings = element_bindings.get(owner_key)
        if not isinstance(owner_bindings, dict):
            owner_bindings = {}

        if param_name or expression:
            owner_bindings[attr.name] = {
                "shared_parameter_name": param_name,
                "shared_parameter_expression": expression,
            }
        else:
            owner_bindings.pop(attr.name, None)

        if owner_bindings:
            element_bindings[owner_key] = owner_bindings
        else:
            element_bindings.pop(owner_key, None)

        if element_bindings:
            bindings[ek] = element_bindings
        else:
            bindings.pop(ek, None)

        setattr(tool.Project.get_project_props(), json_attr_name, json.dumps(bindings))

    def _get_material_set_item_binding_key(material_set_item_id: int) -> str:
        if not material_set_item_id:
            return ""
        ifc_file = tool.Ifc.get()
        material_set_item = ifc_file.by_id(material_set_item_id)
        if not material_set_item:
            return ""

        item_id = material_set_item.id()
        item_class = material_set_item.is_a()

        if item_class == "IfcMaterialLayer":
            for layer_set in ifc_file.by_type("IfcMaterialLayerSet"):
                layers = list(layer_set.MaterialLayers or [])
                for idx, layer in enumerate(layers):
                    if layer and layer.id() == item_id:
                        set_name = layer_set.LayerSetName or ""
                        return f"{item_class}|{set_name}|{idx}"

        if item_class == "IfcMaterialProfile":
            for profile_set in ifc_file.by_type("IfcMaterialProfileSet"):
                profiles = list(profile_set.MaterialProfiles or [])
                for idx, profile in enumerate(profiles):
                    if profile and profile.id() == item_id:
                        set_name = profile_set.Name or ""
                        return f"{item_class}|{set_name}|{idx}"

        if item_class == "IfcMaterialConstituent":
            for constituent_set in ifc_file.by_type("IfcMaterialConstituentSet"):
                constituents = list(constituent_set.MaterialConstituents or [])
                for idx, constituent in enumerate(constituents):
                    if constituent and constituent.id() == item_id:
                        set_name = constituent_set.Name or ""
                        return f"{item_class}|{set_name}|{idx}"

        return ""

    # --- BIMAttributeProperties.attributes (entity-level IFC attrs) ---
    attribute_props = getattr(owner, "BIMAttributeProperties", None)
    if attribute_props is not None:
        in_entity_attrs = ".BIMAttributeProperties.attributes[" in (data_path or "")
        if not in_entity_attrs:
            try:
                in_entity_attrs = any(c.as_pointer() == attr.as_pointer() for c in attribute_props.attributes)
            except Exception:
                in_entity_attrs = False
        if in_entity_attrs:
            _persist_bindings("attribute_expression_bindings_json", "entity_attrs")
            return

    # --- BIMTypeProperties.type_attributes ---
    type_props = getattr(owner, "BIMTypeProperties", None)
    if type_props is not None:
        in_type_attrs = ".BIMTypeProperties.type_attributes[" in (data_path or "")
        if not in_type_attrs:
            try:
                in_type_attrs = any(c.as_pointer() == attr.as_pointer() for c in type_props.type_attributes)
            except Exception:
                in_type_attrs = False
        if in_type_attrs:
            type_element_key = ""
            type_el = ifcopenshell.util.element.get_type(element)
            if type_el:
                type_element_key = (type_el.GlobalId or "").strip()
            if type_element_key:
                _persist_bindings("attribute_expression_bindings_json", "type_attrs", type_element_key)
            return

    # --- Material-set props ---
    mprops = getattr(owner, "BIMObjectMaterialProperties", None)
    if mprops is None:
        return

    in_material_set_item_attrs = ".BIMObjectMaterialProperties.material_set_item_attributes[" in data_path
    if not in_material_set_item_attrs:
        try:
            in_material_set_item_attrs = any(
                candidate.as_pointer() == attr.as_pointer() for candidate in mprops.material_set_item_attributes
            )
        except Exception:
            in_material_set_item_attrs = False
    if in_material_set_item_attrs:
        set_item_id = int(getattr(mprops, "active_material_set_item_id", 0) or 0)
        if set_item_id:
            _persist_bindings("material_set_item_expression_bindings_json", str(set_item_id))
            semantic_key = _get_material_set_item_binding_key(set_item_id)
            if semantic_key:
                _persist_bindings("material_set_item_expression_bindings_json", f"key:{semantic_key}")
        return

    in_material_set_usage_attrs = ".BIMObjectMaterialProperties.material_set_usage_attributes[" in data_path
    if not in_material_set_usage_attrs:
        try:
            in_material_set_usage_attrs = any(
                candidate.as_pointer() == attr.as_pointer() for candidate in mprops.material_set_usage_attributes
            )
        except Exception:
            in_material_set_usage_attrs = False
    if not in_material_set_usage_attrs:
        return

    usage_key = ""
    if element:
        material = ifcopenshell.util.element.get_material(element)
        if material is not None and "Usage" in material.is_a():
            usage_key = f"usage:{material.is_a()}"

    if usage_key:
        _persist_bindings("material_set_usage_expression_bindings_json", usage_key)


def _restore_entity_attribute_expression_bindings(obj: "bpy.types.Object") -> None:
    """Restore expression bindings for BIMAttributeProperties.attributes after import_attributes.

    Called by EnableEditingAttributes after the attribute collection is repopulated
    so that shared_parameter_name / shared_parameter_expression survive .blend reload.
    """
    element = tool.Ifc.get_entity(obj)
    if not element:
        return
    element_key = (element.GlobalId or "").strip()
    if not element_key:
        return

    bindings_raw = getattr(tool.Project.get_project_props(), "attribute_expression_bindings_json", "") or "{}"
    try:
        root = json.loads(bindings_raw)
    except json.JSONDecodeError:
        return
    if not isinstance(root, dict):
        return

    entity_attr_bindings = root.get(element_key, {}).get("entity_attrs", {})
    if not isinstance(entity_attr_bindings, dict) or not entity_attr_bindings:
        return

    props = getattr(obj, "BIMAttributeProperties", None)
    if props is None:
        return

    for attr in props.attributes:
        binding = entity_attr_bindings.get(attr.name)
        if not isinstance(binding, dict):
            continue
        shared_name = (binding.get("shared_parameter_name") or "").strip()
        shared_expr = (binding.get("shared_parameter_expression") or "").strip()
        if not (shared_name or shared_expr):
            continue
        attr.shared_parameter_name = shared_name
        attr.shared_parameter_expression = shared_expr
        _sync_attribute_expression_to_engine(
            attr,
            tool.Blender.get_full_data_path(attr),
            apply_local_expression=False,
        )


def _restore_type_attribute_expression_bindings(obj: "bpy.types.Object") -> None:
    """Restore expression bindings for BIMTypeProperties.type_attributes.

    Called by EnableEditingTypeAttributes after the collection is repopulated so
    that shared_parameter_name / shared_parameter_expression survive .blend reload.
    The bindings are stored under the *type* element's GlobalId, not the instance's.
    """
    element = tool.Ifc.get_entity(obj)
    if not element:
        return
    type_el = ifcopenshell.util.element.get_type(element)
    type_element_key = (type_el.GlobalId or "").strip() if type_el else ""
    if not type_element_key:
        return

    bindings_raw = getattr(tool.Project.get_project_props(), "attribute_expression_bindings_json", "") or "{}"
    try:
        root = json.loads(bindings_raw)
    except json.JSONDecodeError:
        return
    if not isinstance(root, dict):
        return

    type_attr_bindings = root.get(type_element_key, {}).get("type_attrs", {})
    if not isinstance(type_attr_bindings, dict) or not type_attr_bindings:
        return

    props = getattr(obj, "BIMTypeProperties", None)
    if props is None:
        return

    for attr in props.type_attributes:
        binding = type_attr_bindings.get(attr.name)
        if not isinstance(binding, dict):
            continue
        shared_name = (binding.get("shared_parameter_name") or "").strip()
        shared_expr = (binding.get("shared_parameter_expression") or "").strip()
        if not (shared_name or shared_expr):
            continue
        attr.shared_parameter_name = shared_name
        attr.shared_parameter_expression = shared_expr
        _sync_attribute_expression_to_engine(
            attr,
            tool.Blender.get_full_data_path(attr),
            apply_local_expression=False,
        )
