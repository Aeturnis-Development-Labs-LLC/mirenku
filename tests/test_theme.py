"""
Test suite for the theme module (I1) — sv-ttk with the Mirenku accent.
"""

import pytest
import sys
import os
import tkinter as tk
from tkinter import ttk
from unittest.mock import patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ui import theme


class TestResolveMode:
    def test_explicit_light_and_dark(self):
        assert theme.resolve_mode("Light") == "light"
        assert theme.resolve_mode("Dark") == "dark"
        assert theme.resolve_mode("dark") == "dark"

    def test_system_follows_darkdetect(self):
        with patch("darkdetect.theme", return_value="Dark"):
            assert theme.resolve_mode("System") == "dark"
        with patch("darkdetect.theme", return_value="Light"):
            assert theme.resolve_mode("System") == "light"

    def test_system_defaults_light_when_detection_fails(self):
        with patch("darkdetect.theme", side_effect=RuntimeError):
            assert theme.resolve_mode("System") == "light"

    def test_none_preference_defaults_light(self):
        with patch("darkdetect.theme", return_value=None):
            assert theme.resolve_mode(None) == "light"


@pytest.mark.gui
class TestApplyTheme:
    @pytest.fixture(scope="class")
    def root(self):
        root = tk.Tk()
        root.withdraw()
        yield root
        try:
            root.destroy()
        except:
            pass

    def test_light_applies_sun_valley(self, root):
        fonts = theme.apply_theme(root, "Light")
        assert ttk.Style().theme_use() == "sun-valley-light"
        assert theme.current_mode() == "light"
        assert set(fonts) == {"ui", "ui_bold", "data", "heading"}

    def test_dark_applies_sun_valley(self, root):
        theme.apply_theme(root, "Dark")
        assert ttk.Style().theme_use() == "sun-valley-dark"
        assert theme.current_mode() == "dark"

    def test_stripes_follow_mode(self, root):
        theme.apply_theme(root, "Light")
        light_stripes = theme.stripe_colors()
        theme.apply_theme(root, "Dark")
        dark_stripes = theme.stripe_colors()

        assert light_stripes != dark_stripes
        assert light_stripes[0] == "#ffffff"
