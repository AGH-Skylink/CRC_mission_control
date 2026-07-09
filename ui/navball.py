import dearpygui.dearpygui as dpg
import math
import ui.theme as theme


class NavballWidget:
    """Klasyczny navball (attitude indicator) - horyzont niebo/ziemia,
    skala pitch co 10 stopni, obracany pierscien roll, oraz osobne
    wskazniki pitch/roll/yaw na krawedziach. Logika identyczna jak wczesniej,
    zmienily sie tylko kolory/kontrast, zeby lepiej czytac go na nowym,
    ciemnym motywie (i zeby wygladal jak realny navball, a nie kolko ze
    strzalka)."""

    def __init__(self, parent_tag, width=350, height=350):
        self.width = width
        self.height = height
        self.center_x = width / 2
        self.center_y = height / 2
        self.radius = 110

        # "Niebo" - ciemny granat/petrol zamiast plaskiego jasnego teala,
        # zeby kula wygladala trojwymiarowo i nie zlewala sie z akcentem UI.
        self.sky_color = (28, 54, 64)      # #1C3640
        self.ground_color = theme.COLOR_BG_DEEP  # #101314
        self.line_color = theme.COLOR_TEXT_MAIN  # biale/jasne linie skali
        self.ring_color = theme.COLOR_TEXT_MUTED
        self.accent_color = theme.STATUS_AMBER   # wskazniki pitch/roll/yaw

        self.horizon_node = dpg.generate_uuid()
        self.pitch_indicator = dpg.generate_uuid()
        self.roll_indicator = dpg.generate_uuid()
        self.yaw_indicator = dpg.generate_uuid()

        self._build_ui(parent_tag)

    def _build_ui(self, parent_tag):
        with dpg.drawlist(width=self.width, height=self.height, parent=parent_tag):

            with dpg.draw_node(tag=self.horizon_node):
                dpg.draw_rectangle((-400, -400), (400, 0), color=self.sky_color, fill=self.sky_color)
                dpg.draw_rectangle((-400, 0), (400, 400), color=self.ground_color, fill=self.ground_color)

                for i in range(-90, 100, 10):
                    if i == 0:
                        continue
                    y_pos = -(i / 90.0) * self.radius
                    line_width = 40 if i % 20 == 0 else 20
                    dpg.draw_line((-line_width, y_pos), (line_width, y_pos), color=self.line_color, thickness=1)
                    dpg.draw_text((-line_width - 25, y_pos - 7), str(i), size=12, color=self.line_color)

                # Linia horyzontu (0 stopni) - wyraznie grubsza, akcentowana teal
                dpg.draw_line((-400, 0), (400, 0), color=theme.ACCENT_PRIMARY, thickness=2)

            # Maska poza obreb kuli (tlo panelu wokol okregu)
            mask_thickness = 200
            mask_radius = self.radius + (mask_thickness / 2)
            dpg.draw_circle((self.center_x, self.center_y), mask_radius, color=theme.COLOR_PANEL,
                            thickness=mask_thickness)

            # Zewnetrzny pierscien kuli - podwojna obwodka dla glebi
            dpg.draw_circle((self.center_x, self.center_y), self.radius + 4, color=theme.COLOR_BORDER, thickness=1)
            dpg.draw_circle((self.center_x, self.center_y), self.radius, color=self.ring_color, thickness=2)

            c_x, c_y = self.center_x, self.center_y

            # Centralny reticle (staly, nie obraca sie z kula) - klasyczny
            # ksztalt "gullwing" navballa
            dpg.draw_line((c_x - 50, c_y), (c_x - 15, c_y), color=self.accent_color, thickness=3)
            dpg.draw_line((c_x - 15, c_y), (c_x - 15, c_y + 10), color=self.accent_color, thickness=3)
            dpg.draw_line((c_x + 15, c_y), (c_x + 50, c_y), color=self.accent_color, thickness=3)
            dpg.draw_circle((c_x, c_y), 3, color=self.accent_color, fill=self.accent_color)

            # Pasek YAW (gora)
            dpg.draw_rectangle((c_x - 80, c_y - 150), (c_x + 80, c_y - 142), color=theme.COLOR_BORDER,
                               fill=theme.COLOR_BG_DEEP)
            dpg.draw_triangle((c_x, c_y - 146), (c_x - 5, c_y - 136), (c_x + 5, c_y - 136), fill=self.accent_color,
                              tag=self.yaw_indicator)

            # Pasek PITCH (lewa krawedz)
            dpg.draw_rectangle((c_x - 155, c_y - 80), (c_x - 147, c_y + 80), color=theme.COLOR_BORDER,
                               fill=theme.COLOR_BG_DEEP)
            dpg.draw_circle((c_x - 151, c_y), 6, color=self.accent_color, fill=self.accent_color,
                            tag=self.pitch_indicator)

            # Pasek ROLL (prawa krawedz)
            dpg.draw_rectangle((c_x + 147, c_y - 80), (c_x + 155, c_y + 80), color=theme.COLOR_BORDER,
                               fill=theme.COLOR_BG_DEEP)
            dpg.draw_circle((c_x + 151, c_y), 6, color=self.accent_color, fill=self.accent_color,
                            tag=self.roll_indicator)

    def update(self, pitch: float, roll: float, yaw: float):
        pitch_px = (pitch / 90.0) * self.radius

        trans_center = dpg.create_translation_matrix([self.center_x, self.center_y])
        rot_mat = dpg.create_rotation_matrix(math.radians(roll), [0, 0, -1])
        trans_pitch = dpg.create_translation_matrix([0, pitch_px])

        dpg.apply_transform(self.horizon_node, trans_center * rot_mat * trans_pitch)

        yaw_x = self.center_x + (yaw / 180.0) * 80
        dpg.configure_item(self.yaw_indicator, p1=(yaw_x, self.center_y - 146), p2=(yaw_x - 5, self.center_y - 136),
                           p3=(yaw_x + 5, self.center_y - 136))

        p_y = self.center_y - (pitch / 90.0) * 80
        dpg.configure_item(self.pitch_indicator, center=(self.center_x - 151, p_y))

        r_y = self.center_y - (roll / 180.0) * 80
        dpg.configure_item(self.roll_indicator, center=(self.center_x + 151, r_y))
