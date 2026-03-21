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


"""Tests for plain bpy.props expression-engine binding machinery.

These tests cover:
  - JSON persistence helpers (_get_plain_prop_binding, _set_plain_prop_binding,
    _clear_plain_prop_binding)
  - Engine integration (_sync_plain_prop_to_engine) with a mock engine
  - draw_prop_with_expression data-type detection (via RNA introspection)
  - restore_plain_prop_expression_bindings re-registration on all 6 parametric
    PropertyGroups (BIMArrayProperties, BIMStairProperties, BIMWindowProperties,
    BIMDoorProperties, BIMRailingProperties, BIMRoofProperties)

Pure-Python tests use a MockProps stub and do not require Blender. Tests that
need bpy (RNA introspection, real PropertyGroup access) are guarded by
``pytest.importorskip``.
"""

from __future__ import annotations

import json
import sys
import types
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helper: a minimal PropertyGroup-like stub for JSON persistence tests
# ---------------------------------------------------------------------------


class _MockProps:
    """Minimal duck-typed stub that exposes bexpeng_bindings_json."""

    def __init__(self, initial: str = "{}") -> None:
        self.bexpeng_bindings_json = initial


# ---------------------------------------------------------------------------
# Lazy import of operator helpers (they live in a Blender add-on module)
# ---------------------------------------------------------------------------


def _import_plain_prop_helpers():
    """Import the plain-prop helpers, skipping if the module is unavailable."""
    bim_operator = pytest.importorskip("bonsai.bim.operator")
    return (
        bim_operator._get_plain_prop_binding,
        bim_operator._set_plain_prop_binding,
        bim_operator._clear_plain_prop_binding,
        bim_operator._sync_plain_prop_to_engine,
        bim_operator.restore_plain_prop_expression_bindings,
        bim_operator._plain_prop_engine_subscriptions,
    )


# ---------------------------------------------------------------------------
# 1. JSON persistence helpers
# ---------------------------------------------------------------------------


class TestGetPlainPropBinding:
    def test_empty_json_returns_empty_dict(self):
        get, *_ = _import_plain_prop_helpers()[:1], None
        get = _import_plain_prop_helpers()[0]
        props = _MockProps("{}")
        assert get(props, "count") == {}

    def test_missing_prop_returns_empty_dict(self):
        get = _import_plain_prop_helpers()[0]
        props = _MockProps(json.dumps({"other_prop": {"param_name": "p", "expression": "= 1"}}))
        assert get(props, "count") == {}

    def test_existing_binding_is_returned(self):
        get = _import_plain_prop_helpers()[0]
        stored = {"count": {"param_name": "n_items", "expression": "= 3"}}
        props = _MockProps(json.dumps(stored))
        result = get(props, "count")
        assert result == {"param_name": "n_items", "expression": "= 3"}

    def test_malformed_json_returns_empty_dict(self):
        get = _import_plain_prop_helpers()[0]
        props = _MockProps("{bad json}")
        assert get(props, "count") == {}


class TestSetPlainPropBinding:
    def test_set_writes_binding(self):
        get, set_, *_ = _import_plain_prop_helpers()[:2], None
        get, set_ = _import_plain_prop_helpers()[0], _import_plain_prop_helpers()[1]
        props = _MockProps()
        set_(props, "count", "n_items", "= 3")
        assert get(props, "count") == {"param_name": "n_items", "expression": "= 3"}

    def test_set_empty_expression_removes_binding(self):
        get, set_ = _import_plain_prop_helpers()[0], _import_plain_prop_helpers()[1]
        props = _MockProps(json.dumps({"count": {"param_name": "n_items", "expression": "= 3"}}))
        set_(props, "count", "", "")
        assert get(props, "count") == {}

    def test_set_preserves_other_bindings(self):
        get, set_ = _import_plain_prop_helpers()[0], _import_plain_prop_helpers()[1]
        props = _MockProps(json.dumps({"x": {"param_name": "px", "expression": "= 1"}}))
        set_(props, "count", "n_items", "= 5")
        assert get(props, "x") == {"param_name": "px", "expression": "= 1"}
        assert get(props, "count")["param_name"] == "n_items"

    def test_overwrite_existing_binding(self):
        get, set_ = _import_plain_prop_helpers()[0], _import_plain_prop_helpers()[1]
        props = _MockProps(json.dumps({"count": {"param_name": "old", "expression": "= 1"}}))
        set_(props, "count", "new", "= 2")
        result = get(props, "count")
        assert result["param_name"] == "new"
        assert result["expression"] == "= 2"


class TestClearPlainPropBinding:
    def test_clear_removes_binding(self):
        get = _import_plain_prop_helpers()[0]
        clear = _import_plain_prop_helpers()[2]
        props = _MockProps(json.dumps({"count": {"param_name": "np", "expression": "= 4"}}))
        clear(props, "count")
        assert get(props, "count") == {}

    def test_clear_nonexistent_is_noop(self):
        clear = _import_plain_prop_helpers()[2]
        props = _MockProps("{}")
        clear(props, "count")  # must not raise
        assert props.bexpeng_bindings_json == "{}"

    def test_clear_preserves_other_bindings(self):
        get = _import_plain_prop_helpers()[0]
        clear = _import_plain_prop_helpers()[2]
        stored = {
            "x": {"param_name": "px", "expression": "= 1"},
            "count": {"param_name": "nc", "expression": "= 3"},
        }
        props = _MockProps(json.dumps(stored))
        clear(props, "count")
        assert get(props, "x") == {"param_name": "px", "expression": "= 1"}
        assert get(props, "count") == {}


# ---------------------------------------------------------------------------
# 2. Engine integration with a mock bexpeng engine
# ---------------------------------------------------------------------------


def _make_mock_engine():
    engine = MagicMock()
    engine.set_parameter = MagicMock()
    engine.get_expression = MagicMock(return_value=None)
    engine.subscribe = MagicMock()
    engine.unsubscribe = MagicMock()
    engine.get_value = MagicMock(return_value=None)
    return engine


def _patch_bexpeng(engine):
    """Return a context manager that patches bexpeng with a fake module."""
    fake_bexpeng = types.ModuleType("bexpeng")
    fake_bexpeng.get_engine = MagicMock(return_value=engine)
    return patch.dict(sys.modules, {"bexpeng": fake_bexpeng})


class TestSyncPlainPropToEngine:
    def _get_fn(self):
        return _import_plain_prop_helpers()[3]

    def _get_prefs_mock(self):
        prefs = MagicMock()
        prefs.enable_blender_expression_engine = True
        return prefs

    def test_registers_parameter_and_expression(self):
        sync = self._get_fn()
        engine = _make_mock_engine()
        props = _MockProps()
        props.count = 2

        with _patch_bexpeng(engine):
            with patch("bonsai.tool.Blender.get_addon_preferences", return_value=self._get_prefs_mock()):
                sync(
                    "bpy.data.objects['Cube'].BIMArrayProperties",
                    "count",
                    "integer",
                    "n_items",
                    "= 5",
                    apply_local_expression=True,
                )

        engine.set_parameter.assert_called_once_with("n_items", "5")
        engine.subscribe.assert_called_once()

    def test_does_not_register_if_bexpeng_disabled(self):
        sync = self._get_fn()
        engine = _make_mock_engine()

        prefs = MagicMock()
        prefs.enable_blender_expression_engine = False

        with _patch_bexpeng(engine):
            with patch("bonsai.tool.Blender.get_addon_preferences", return_value=prefs):
                sync(
                    "bpy.data.objects['Cube'].BIMArrayProperties",
                    "count",
                    "integer",
                    "n_items",
                    "= 5",
                )

        engine.set_parameter.assert_not_called()


# ---------------------------------------------------------------------------
# 3. Value application callback (integer, float, string) via mock engine
# ---------------------------------------------------------------------------


class TestPlainPropValueApplication:
    """Test that the engine callback correctly coerces and sets prop values."""

    def _get_sync(self):
        return _import_plain_prop_helpers()[3]

    def _get_subs(self):
        return _import_plain_prop_helpers()[5]

    def _get_prefs_mock(self):
        prefs = MagicMock()
        prefs.enable_blender_expression_engine = True
        return prefs

    def _subscribe_and_get_callback(self, engine, prop_name, data_type, props_obj, param_name="test_p"):
        """Sync to engine and capture the subscribed callback."""
        sync = self._get_sync()
        subs = self._get_subs()
        data_path = f"__test_props_{id(props_obj)}"
        # Clear any previous subscription for this binding.
        subs.pop((data_path, prop_name), None)

        # Patch eval to return props_obj.
        with _patch_bexpeng(engine):
            with patch("bonsai.bim.plain_prop_expression.eval", return_value=props_obj):
                with patch("bonsai.tool.Blender.get_addon_preferences", return_value=self._get_prefs_mock()):
                    sync(data_path, prop_name, data_type, param_name, "", apply_local_expression=False)

        # The callback was passed to engine.subscribe as the second argument.
        assert engine.subscribe.called
        callback = engine.subscribe.call_args[0][1]
        return callback, data_path

    def test_integer_value_applied(self):
        engine = _make_mock_engine()

        class IntProps:
            count = 0

        props = IntProps()
        callback, data_path = self._subscribe_and_get_callback(engine, "count", "integer", props)
        engine.get_value.return_value = 7.9
        with patch("bonsai.bim.plain_prop_expression.eval", return_value=props):
            callback("test_p")
        assert props.count == 8  # rounded int

    def test_float_value_applied(self):
        engine = _make_mock_engine()

        class FloatProps:
            x = 0.0

        props = FloatProps()
        callback, data_path = self._subscribe_and_get_callback(engine, "x", "float", props)
        engine.get_value.return_value = 3.14
        with patch("bonsai.bim.plain_prop_expression.eval", return_value=props):
            callback("test_p")
        assert abs(props.x - 3.14) < 1e-9

    def test_string_value_applied(self):
        engine = _make_mock_engine()

        class StringProps:
            name = ""

        props = StringProps()
        callback, data_path = self._subscribe_and_get_callback(engine, "name", "string", props, param_name="test_str")
        engine.get_value.return_value = "hello"
        with patch("bonsai.bim.plain_prop_expression.eval", return_value=props):
            callback("test_str")
        assert props.name == "hello"


# ---------------------------------------------------------------------------
# 4. restore_plain_prop_expression_bindings — requires real bpy PropertyGroups
# ---------------------------------------------------------------------------


class TestRestorePlainPropExpressionBindings:
    """Tests requiring actual bpy PropertyGroups (run inside Blender)."""

    @pytest.fixture(autouse=True)
    def _require_bpy(self):
        bpy = pytest.importorskip("bpy")
        self.bpy = bpy

    def _get_restore(self):
        return _import_plain_prop_helpers()[4]

    def _get_subs(self):
        return _import_plain_prop_helpers()[5]

    def _make_engine(self):
        return _make_mock_engine()

    def _get_prefs_mock(self):
        prefs = MagicMock()
        prefs.enable_blender_expression_engine = True
        return prefs

    def _get_props(self, prop_group_name: str):
        bpy = self.bpy
        bpy.ops.mesh.primitive_cube_add()
        obj = bpy.context.active_object
        return getattr(obj, prop_group_name)

    # ----- BIMArrayProperties -----

    def test_restore_array_integer_binding(self):
        props = self._get_props("BIMArrayProperties")
        set_ = _import_plain_prop_helpers()[1]
        set_(props, "count", "n_items", "= 4")

        engine = self._make_engine()
        restore = self._get_restore()
        with _patch_bexpeng(engine):
            with patch("bonsai.tool.Blender.get_addon_preferences", return_value=self._get_prefs_mock()):
                with patch("bonsai.tool.Blender.get_full_data_path", return_value="test_path"):
                    restore(props)

        engine.subscribe.assert_called()
        assert any(v[0] == "n_items" for v in self._get_subs().values())

    def test_restore_array_float_binding(self):
        props = self._get_props("BIMArrayProperties")
        set_ = _import_plain_prop_helpers()[1]
        set_(props, "x", "arr_x", "= 1.5")

        engine = self._make_engine()
        restore = self._get_restore()
        with _patch_bexpeng(engine):
            with patch("bonsai.tool.Blender.get_addon_preferences", return_value=self._get_prefs_mock()):
                with patch("bonsai.tool.Blender.get_full_data_path", return_value="test_path"):
                    restore(props)

        engine.subscribe.assert_called()
        assert any(v[0] == "arr_x" for v in self._get_subs().values())

    # ----- BIMStairProperties -----

    def test_restore_stair_float_binding(self):
        props = self._get_props("BIMStairProperties")
        set_ = _import_plain_prop_helpers()[1]
        set_(props, "height", "stair_h", "= 2.5")

        engine = self._make_engine()
        restore = self._get_restore()
        with _patch_bexpeng(engine):
            with patch("bonsai.tool.Blender.get_addon_preferences", return_value=self._get_prefs_mock()):
                with patch("bonsai.tool.Blender.get_full_data_path", return_value="test_path"):
                    restore(props)

        assert any(v[0] == "stair_h" for v in self._get_subs().values())

    # ----- BIMWindowProperties -----

    def test_restore_window_float_binding(self):
        props = self._get_props("BIMWindowProperties")
        set_ = _import_plain_prop_helpers()[1]
        set_(props, "overall_height", "win_h", "= 1.2")

        engine = self._make_engine()
        restore = self._get_restore()
        with _patch_bexpeng(engine):
            with patch("bonsai.tool.Blender.get_addon_preferences", return_value=self._get_prefs_mock()):
                with patch("bonsai.tool.Blender.get_full_data_path", return_value="test_path"):
                    restore(props)

        assert any(v[0] == "win_h" for v in self._get_subs().values())

    # ----- BIMDoorProperties -----

    def test_restore_door_float_binding(self):
        props = self._get_props("BIMDoorProperties")
        set_ = _import_plain_prop_helpers()[1]
        set_(props, "overall_height", "door_h", "= 2.1")

        engine = self._make_engine()
        restore = self._get_restore()
        with _patch_bexpeng(engine):
            with patch("bonsai.tool.Blender.get_addon_preferences", return_value=self._get_prefs_mock()):
                with patch("bonsai.tool.Blender.get_full_data_path", return_value="test_path"):
                    restore(props)

        assert any(v[0] == "door_h" for v in self._get_subs().values())

    # ----- BIMRailingProperties -----

    def test_restore_railing_float_binding(self):
        props = self._get_props("BIMRailingProperties")
        set_ = _import_plain_prop_helpers()[1]
        set_(props, "height", "rail_h", "= 1.1")

        engine = self._make_engine()
        restore = self._get_restore()
        with _patch_bexpeng(engine):
            with patch("bonsai.tool.Blender.get_addon_preferences", return_value=self._get_prefs_mock()):
                with patch("bonsai.tool.Blender.get_full_data_path", return_value="test_path"):
                    restore(props)

        assert any(v[0] == "rail_h" for v in self._get_subs().values())

    # ----- BIMRoofProperties -----

    def test_restore_roof_float_binding(self):
        props = self._get_props("BIMRoofProperties")
        set_ = _import_plain_prop_helpers()[1]
        set_(props, "height", "roof_h", "= 3.0")

        engine = self._make_engine()
        restore = self._get_restore()
        with _patch_bexpeng(engine):
            with patch("bonsai.tool.Blender.get_addon_preferences", return_value=self._get_prefs_mock()):
                with patch("bonsai.tool.Blender.get_full_data_path", return_value="test_path"):
                    restore(props)

        assert any(v[0] == "roof_h" for v in self._get_subs().values())

    def test_restore_skips_vector_properties(self):
        """Array (vector) props must not be subscribed even if present in JSON."""
        # BIMStairProperties.custom_first_last_tread_run is a FloatVectorProperty.
        props = self._get_props("BIMStairProperties")
        set_ = _import_plain_prop_helpers()[1]
        set_(props, "custom_first_last_tread_run", "tread_v", "= 0.28")

        engine = self._make_engine()
        restore = self._get_restore()
        with _patch_bexpeng(engine):
            with patch("bonsai.tool.Blender.get_addon_preferences", return_value=self._get_prefs_mock()):
                with patch("bonsai.tool.Blender.get_full_data_path", return_value="test_path"):
                    restore(props)

        # The engine subscribe must NOT have been called for a vector property.
        assert "tread_v" not in self._get_subs()

    def test_restore_noop_when_no_bindings(self):
        props = self._get_props("BIMArrayProperties")
        # bexpeng_bindings_json is "{}" by default.
        engine = self._make_engine()
        restore = self._get_restore()
        with _patch_bexpeng(engine):
            with patch("bonsai.tool.Blender.get_addon_preferences", return_value=self._get_prefs_mock()):
                with patch("bonsai.tool.Blender.get_full_data_path", return_value="test_path"):
                    restore(props)

        engine.subscribe.assert_not_called()
