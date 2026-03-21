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

"""Plain bpy.props expression-engine integration helpers.

Extracted from bonsai.bim.operator to break the circular import that arose
when parametric-geometry modules (model/array.py, model/door.py, …) imported
``restore_plain_prop_expression_bindings`` from ``operator.py`` while
``operator.py`` was itself still being initialised (it imports from ui.py
which imports from model/prop.py which imports from model/door.py).

Keeping this machinery in a leaf module with no dependency on ui.py or
model/prop.py resolves the cycle.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import bpy
import bonsai.tool as tool

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# BExpEng availability helpers (shared with operator.py)
# ---------------------------------------------------------------------------


def _is_bexpeng_enabled() -> bool:
    try:
        prefs = tool.Blender.get_addon_preferences()
        if not prefs.enable_blender_expression_engine:
            return False
        import addon_utils

        _loaded_default, loaded_state = addon_utils.check("bexpeng")
        if not loaded_state:
            prefs.enable_blender_expression_engine = False
            return False
        return True
    except Exception:
        return True


def _is_bexpeng_available() -> bool:
    if not _is_bexpeng_enabled():
        return False
    try:
        import bexpeng  # noqa: F401

        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# Plain bpy.props expression-engine machinery
# ---------------------------------------------------------------------------

_plain_prop_engine_subscriptions: dict[tuple[str, str], tuple[str, object]] = {}
"""key: (props_data_path, prop_name) → (param_name, callback)"""


def _get_plain_prop_binding(props: "bpy.types.PropertyGroup", prop_name: str) -> dict:
    """Return the binding dict for *prop_name* from props.bexpeng_bindings_json (or {})."""
    raw = getattr(props, "bexpeng_bindings_json", "{}") or "{}"
    try:
        bindings = json.loads(raw)
        return bindings.get(prop_name) or {}
    except json.JSONDecodeError:
        return {}


def _set_plain_prop_binding(props: "bpy.types.PropertyGroup", prop_name: str, param_name: str, expression: str) -> None:
    """Write (or clear) a binding entry into props.bexpeng_bindings_json."""
    raw = getattr(props, "bexpeng_bindings_json", "{}") or "{}"
    try:
        bindings = json.loads(raw)
        if not isinstance(bindings, dict):
            bindings = {}
    except json.JSONDecodeError:
        bindings = {}
    if param_name or expression:
        bindings[prop_name] = {"param_name": param_name, "expression": expression}
    else:
        bindings.pop(prop_name, None)
    props.bexpeng_bindings_json = json.dumps(bindings)


def _clear_plain_prop_binding(props: "bpy.types.PropertyGroup", prop_name: str) -> None:
    """Remove binding entry for *prop_name* from props.bexpeng_bindings_json."""
    _set_plain_prop_binding(props, prop_name, "", "")


def _sync_plain_prop_to_engine(
    props_data_path: str,
    prop_name: str,
    data_type: str,
    param_name: str,
    expression: str,
    *,
    apply_local_expression: bool = True,
) -> None:
    """Register/replace a plain bpy.prop binding in the expression engine.

    *props_data_path* is the full Python eval path to the PropertyGroup (via
    ``tool.Blender.get_full_data_path(props)``).
    *data_type* must be one of ``"integer"``, ``"float"``, or ``"string"``.
    """
    if not _is_bexpeng_enabled():
        return
    if not _is_bexpeng_available():
        return

    import bexpeng

    engine = bexpeng.get_engine()

    # Remove stale subscription for this binding (props_data_path, prop_name) if any.
    # Keyed by binding identity so multiple props sharing the same param_name
    # each keep their own subscription and the ref count is correct.
    binding_key = (props_data_path, prop_name)
    old = _plain_prop_engine_subscriptions.get(binding_key)
    if old is not None:
        try:
            engine.unsubscribe(old[0], old[1])
        except Exception:
            pass

    def _on_plain_prop_changed(name: str) -> None:
        value = engine.get_value(name)
        if value is None:
            return
        try:
            resolved_props = eval(props_data_path)  # noqa: S307 – trusted internal path
        except Exception:
            return
        try:
            if data_type == "integer":
                coerced = int(round(float(value)))
            elif data_type == "float":
                coerced = float(value)
            else:
                coerced = str(value)
            setattr(resolved_props, prop_name, coerced)
        except Exception:
            pass

    _plain_prop_engine_subscriptions[binding_key] = (param_name, _on_plain_prop_changed)

    # Strip leading "=" accepted in Bonsai's UI expression notation.
    clean_expression = expression[1:].strip() if expression.startswith("=") else expression

    engine.subscribe(param_name, _on_plain_prop_changed)

    if apply_local_expression:
        if clean_expression:
            # set_parameter creates/updates the parameter, evaluates it, and notifies
            # subscribers (including _on_plain_prop_changed registered above).
            engine.set_parameter(param_name, clean_expression)
        elif engine.get_expression(param_name) is None:
            # No expression; seed the engine with the current prop value if not yet known.
            try:
                resolved_props = eval(props_data_path)  # noqa: S307
                initial_value: object = getattr(resolved_props, prop_name, 0)
            except Exception:
                initial_value = 0 if data_type in ("integer", "float") else ""
            engine.set_parameter(param_name, str(initial_value))
    else:
        # Restore path: bexpeng manages its own state; just sync UI with current engine value.
        if engine.get_expression(param_name) is not None:
            _on_plain_prop_changed(param_name)


def _clear_plain_prop_expression_from_engine(props_data_path: str, prop_name: str) -> None:
    """Drop Bonsai's local subscription for the binding at *(props_data_path, prop_name)*.

    Parameter/expression lifetime in the engine is managed by bexpeng itself
    (via its own reference counting).  Bonsai only removes its callback.
    """
    if not _is_bexpeng_available():
        return
    import bexpeng

    engine = bexpeng.get_engine()
    old = _plain_prop_engine_subscriptions.pop((props_data_path, prop_name), None)
    if old is not None:
        try:
            engine.unsubscribe(old[0], old[1])
        except Exception:
            pass


def restore_plain_prop_expression_bindings(props: "bpy.types.PropertyGroup") -> None:
    """Re-register all bexpeng subscriptions from props.bexpeng_bindings_json.

    Called by each parametric-geometry enable-editing operator after loading
    property values from IFC so that live engine callbacks are wired back up
    following a file reload.
    """
    if not _is_bexpeng_enabled():
        return

    raw = getattr(props, "bexpeng_bindings_json", "{}") or "{}"
    try:
        bindings = json.loads(raw)
        if not isinstance(bindings, dict):
            return
    except json.JSONDecodeError:
        return

    props_data_path = tool.Blender.get_full_data_path(props)
    rna_type_map = {"INT": "integer", "FLOAT": "float", "STRING": "string"}

    for prop_name, binding in bindings.items():
        if not isinstance(binding, dict):
            continue
        param_name = (binding.get("param_name") or "").strip()
        expression = (binding.get("expression") or "").strip()
        if not (param_name or expression):
            continue

        rna_prop = props.bl_rna.properties.get(prop_name)
        if rna_prop is None:
            continue
        if getattr(rna_prop, "is_array", False):
            continue
        data_type = rna_type_map.get(rna_prop.type, "")
        if not data_type:
            continue

        _sync_plain_prop_to_engine(
            props_data_path,
            prop_name,
            data_type,
            param_name,
            expression,
            apply_local_expression=False,
        )
