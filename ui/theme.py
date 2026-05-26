import dearpygui.dearpygui as dpg
import logging
import os

COLOR_TEAL = (9, 108, 108)  # #096C6C
COLOR_LIGHT_GRAY = (196, 196, 196)  # #C4C4C4
COLOR_BLACK = (0, 0, 0)  # #000000
COLOR_DARK_BLUE = (22, 53, 77)  # #16354D

ACCENT_PRIMARY = COLOR_TEAL
ACCENT_TRANS = (9, 108, 108, 100)
BG_PANEL = COLOR_BLACK
BG_CHILD = COLOR_DARK_BLUE
TEXT_NORMAL = COLOR_LIGHT_GRAY
TEXT_MAIN = (255, 255, 255)

STATUS_RED = (230, 50, 50)
STATUS_GREEN = (50, 230, 50)
STATUS_BLUE = (0, 119, 255)
STATUS_AMBER = (255, 191, 0)


def apply_skylink_theme():
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, COLOR_BLACK)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, COLOR_DARK_BLUE)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, COLOR_TEAL)
            dpg.add_theme_color(dpg.mvThemeCol_Text, TEXT_NORMAL)
            dpg.add_theme_color(dpg.mvThemeCol_Button, (30, 70, 100))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, COLOR_TEAL)
            dpg.add_theme_color(dpg.mvThemeCol_TabActive, COLOR_TEAL)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (10, 25, 40))
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark, COLOR_TEAL)
            dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 0)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 4)

        with dpg.theme_component(dpg.mvPlot):
            dpg.add_theme_color(dpg.mvPlotCol_PlotBg, (5, 15, 25), category=dpg.mvThemeCat_Plots)
            dpg.add_theme_color(dpg.mvPlotCol_PlotBorder, COLOR_TEAL, category=dpg.mvThemeCat_Plots)
            dpg.add_theme_color(dpg.mvPlotCol_Line, COLOR_TEAL, category=dpg.mvThemeCat_Plots)

    dpg.bind_theme(global_theme)


def setup_fonts():
    logger = logging.getLogger("MissionControl")
    font_path = "assets/fonts/Inter-Regular.ttf"

    if not os.path.exists(font_path):
        return None

    try:
        with dpg.font_registry():
            with dpg.font(font_path, 15) as default_font:
                dpg.add_font_range_hint(dpg.mvFontRangeHint_Default)

            with dpg.font(font_path, 32) as big_font:
                dpg.add_font_range_hint(dpg.mvFontRangeHint_Default)
            dpg.add_alias("big_payload_font", big_font)

            dpg.bind_font(default_font)
            return default_font
    except Exception as e:
        logger.error(f"Błąd czcionek: {e}")
        return None


def create_button_theme(color):
    with dpg.theme() as btn_theme:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, color)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (color[0], color[1], color[2], 200))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (color[0], color[1], color[2], 150))
    return btn_theme