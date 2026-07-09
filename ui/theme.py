import dearpygui.dearpygui as dpg
import logging
import os

# ---------------------------------------------------------------------------
# CRC Mission Control -- nowoczesny, ciemny motyw ("mission deck")
# Paleta: grafitowe tla + jeden akcent (teal), statusy semantyczne osobno.
# ---------------------------------------------------------------------------

COLOR_BG = (21, 24, 26)          # #15181A - tlo glownego okna
COLOR_BG_DEEP = (16, 19, 20)     # #101314 - terminale / wglebienia
COLOR_PANEL = (26, 30, 32)       # #1A1E20 - karty / child_window
COLOR_BORDER = (36, 40, 43)      # #24282B - obramowania kart

COLOR_TEAL = (62, 207, 142)      # #3ECF8E - akcent glowny
COLOR_TEAL_DIM = (30, 46, 38)    # #1E2E26 - teal jako tlo pigulki/statusu
COLOR_TEAL_TRANS = (62, 207, 142, 90)

COLOR_TEXT_MAIN = (236, 238, 239)   # #ECEEEF - tekst pierwszoplanowy
COLOR_TEXT_NORMAL = (154, 160, 165) # #9AA0A5 - tekst drugoplanowy
COLOR_TEXT_MUTED = (125, 132, 137)  # #7D8489 - etykiety / opisy

# Legacy aliasy (uzywane w innych plikach ui/*) - zostawione, zeby nie
# trzeba bylo zmieniac kazdego odwolania do theme.COLOR_*
COLOR_LIGHT_GRAY = COLOR_TEXT_NORMAL
COLOR_BLACK = COLOR_BG_DEEP
COLOR_DARK_BLUE = COLOR_PANEL

ACCENT_PRIMARY = COLOR_TEAL
ACCENT_TRANS = COLOR_TEAL_TRANS
BG_PANEL = COLOR_BG_DEEP
BG_CHILD = COLOR_PANEL
TEXT_NORMAL = COLOR_TEXT_NORMAL
TEXT_MAIN = COLOR_TEXT_MAIN

STATUS_RED = (224, 85, 85)      # #E05555
STATUS_GREEN = (62, 207, 142)   # #3ECF8E (spojny z akcentem)
STATUS_BLUE = (133, 183, 235)   # #85B7EB
STATUS_AMBER = (224, 179, 77)   # #E0B34D

STATUS_RED_DIM = (51, 26, 26)     # #331A1A - tlo pod czerwonym statusem
STATUS_AMBER_DIM = (51, 44, 23)   # #332C17 - tlo pod amber statusem
STATUS_GREEN_DIM = COLOR_TEAL_DIM


def _safe_color(const_name, value, category=None):
    """Dodaje theme_color tylko jesli zainstalowana wersja DearPyGui posiada
    dana stala (nazwy mvThemeCol_*/mvPlotCol_* roznia sie miedzy wersjami
    1.x i 2.x). Brakujaca stala jest po prostu pomijana zamiast wywalac
    caly program przy starcie."""
    const = getattr(dpg, const_name, None)
    if const is None:
        return
    if category is not None:
        dpg.add_theme_color(const, value, category=category)
    else:
        dpg.add_theme_color(const, value)


def _safe_style(const_name, *values):
    const = getattr(dpg, const_name, None)
    if const is None:
        return
    dpg.add_theme_style(const, *values)


def apply_skylink_theme():
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            # Tla
            _safe_color("mvThemeCol_WindowBg", COLOR_BG)
            _safe_color("mvThemeCol_ChildBg", COLOR_PANEL)
            _safe_color("mvThemeCol_PopupBg", COLOR_PANEL)
            _safe_color("mvThemeCol_Border", COLOR_BORDER)
            _safe_color("mvThemeCol_Separator", COLOR_BORDER)

            # Tekst
            _safe_color("mvThemeCol_Text", COLOR_TEXT_NORMAL)
            _safe_color("mvThemeCol_TextDisabled", COLOR_TEXT_MUTED)

            # Zakladki (taby) - aktywna zakladka podswietlona teal, reszta neutralna
            # (nazwy stalych roznia sie miedzy DPG 1.x i 2.x, dlatego probujemy obu wariantow)
            _safe_color("mvThemeCol_Tab", COLOR_PANEL)
            _safe_color("mvThemeCol_TabHovered", (34, 39, 42))
            _safe_color("mvThemeCol_TabActive", COLOR_TEAL_DIM)
            _safe_color("mvThemeCol_TabSelected", COLOR_TEAL_DIM)
            _safe_color("mvThemeCol_TabUnfocused", COLOR_PANEL)
            _safe_color("mvThemeCol_TabUnfocusedActive", COLOR_TEAL_DIM)
            _safe_color("mvThemeCol_TabDimmed", COLOR_PANEL)
            _safe_color("mvThemeCol_TabDimmedSelected", COLOR_TEAL_DIM)

            # Przyciski - neutralny grafit, hover/active podbite
            _safe_color("mvThemeCol_Button", (28, 32, 35))
            _safe_color("mvThemeCol_ButtonHovered", (34, 39, 42))
            _safe_color("mvThemeCol_ButtonActive", COLOR_TEAL_DIM)

            # Pola danych wejsciowych
            _safe_color("mvThemeCol_FrameBg", COLOR_BG_DEEP)
            _safe_color("mvThemeCol_FrameBgHovered", (24, 28, 30))
            _safe_color("mvThemeCol_FrameBgActive", (24, 28, 30))
            _safe_color("mvThemeCol_CheckMark", COLOR_TEAL)

            # Naglowki okien / list
            _safe_color("mvThemeCol_Header", COLOR_TEAL_DIM)
            _safe_color("mvThemeCol_HeaderHovered", (34, 39, 42))
            _safe_color("mvThemeCol_HeaderActive", COLOR_TEAL_DIM)
            _safe_color("mvThemeCol_TitleBgActive", COLOR_TEAL_DIM)

            # Scrollbar
            _safe_color("mvThemeCol_ScrollbarBg", COLOR_BG_DEEP)
            _safe_color("mvThemeCol_ScrollbarGrab", (40, 45, 48))
            _safe_color("mvThemeCol_ScrollbarGrabHovered", (52, 58, 62))
            _safe_color("mvThemeCol_ScrollbarGrabActive", COLOR_TEAL_DIM)

            # Geometria / spacing - lekko zaokraglone karty, wiecej oddechu
            _safe_style("mvStyleVar_WindowBorderSize", 0)
            _safe_style("mvStyleVar_ChildBorderSize", 1)
            _safe_style("mvStyleVar_FrameBorderSize", 0)
            _safe_style("mvStyleVar_ChildRounding", 10)
            _safe_style("mvStyleVar_FrameRounding", 6)
            _safe_style("mvStyleVar_GrabRounding", 6)
            _safe_style("mvStyleVar_TabRounding", 6)
            _safe_style("mvStyleVar_PopupRounding", 8)
            _safe_style("mvStyleVar_WindowPadding", 14, 14)
            # Uwaga: trzymamy FramePadding/ItemSpacing blisko domyslnych DPG.
            # Wieksze wartosci (np. 10,6) rozdymaly przyciski o STALEJ
            # szerokosci (np. QUICK COMMANDS w zakladce FLIGHT) do tego
            # stopnia, ze tekst przestawal miescic sie w rzedzie, wiersz
            # przekraczal wysokosc kontenera i DPG dokladal scrollbar -
            # co wygladalo jak "pionowy suwak, ktory przy przeciaganiu
            # ucieka w bok".
            _safe_style("mvStyleVar_FramePadding", 8, 4)
            _safe_style("mvStyleVar_ItemSpacing", 6, 6)
            _safe_style("mvStyleVar_ItemInnerSpacing", 5, 5)

        with dpg.theme_component(dpg.mvPlot):
            cat = dpg.mvThemeCat_Plots
            _safe_color("mvPlotCol_PlotBg", COLOR_BG_DEEP, category=cat)
            _safe_color("mvPlotCol_PlotBorder", COLOR_BORDER, category=cat)
            _safe_color("mvPlotCol_Line", COLOR_TEAL, category=cat)
            _safe_color("mvPlotCol_FrameBg", COLOR_PANEL, category=cat)
            _safe_color("mvPlotCol_LegendBg", COLOR_PANEL, category=cat)
            # Siatka osi - w DPG 1.x to mvPlotCol_XAxisGrid/YAxisGrid,
            # w niektorych 2.x buildach zbiorczo mvPlotCol_AxisGrid.
            _safe_color("mvPlotCol_XAxisGrid", COLOR_BORDER, category=cat)
            _safe_color("mvPlotCol_YAxisGrid", COLOR_BORDER, category=cat)
            _safe_color("mvPlotCol_AxisGrid", COLOR_BORDER, category=cat)

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
    """Tworzy motyw przycisku w podanym kolorze pelnym (RGB/RGBA) -
    uzywane dla przyciskow semantycznych (ARM = teal, ABORT = czerwony itd.)."""
    with dpg.theme() as btn_theme:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (color[0], color[1], color[2], 40))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (color[0], color[1], color[2], 70))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (color[0], color[1], color[2], 100))
            dpg.add_theme_color(dpg.mvThemeCol_Text, color)
            dpg.add_theme_color(dpg.mvThemeCol_Border, (color[0], color[1], color[2], 90))
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)
    return btn_theme
