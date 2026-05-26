import dearpygui.dearpygui as dpg
import math
import ui.theme as theme


class NavballWidget:
    def __init__(self, parent_tag, width=350, height=350):
        self.width = width
        self.height = height
        self.center_x = width / 2
        self.center_y = height / 2
        self.radius = 110

        self.sky_color = theme.COLOR_TEAL
        self.ground_color = theme.COLOR_BLACK
        self.line_color = theme.COLOR_LIGHT_GRAY
        self.accent_color = theme.STATUS_AMBER

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
                    if i == 0: continue
                    y_pos = -(i / 90.0) * self.radius
                    line_width = 40 if i % 20 == 0 else 20
                    dpg.draw_line((-line_width, y_pos), (line_width, y_pos), color=self.line_color, thickness=1)
                    dpg.draw_text((-line_width - 25, y_pos - 7), str(i), size=12, color=self.line_color)

                dpg.draw_line((-400, 0), (400, 0), color=theme.COLOR_LIGHT_GRAY, thickness=2)

            mask_thickness = 200
            mask_radius = self.radius + (mask_thickness / 2)
            dpg.draw_circle((self.center_x, self.center_y), mask_radius, color=theme.BG_PANEL,
                            thickness=mask_thickness)

            dpg.draw_circle((self.center_x, self.center_y), self.radius, color=theme.ACCENT_PRIMARY, thickness=2)

            c_x, c_y = self.center_x, self.center_y
            dpg.draw_line((c_x - 50, c_y), (c_x - 15, c_y), color=theme.STATUS_AMBER, thickness=3)
            dpg.draw_line((c_x - 15, c_y), (c_x - 15, c_y + 10), color=theme.STATUS_AMBER, thickness=3)
            dpg.draw_line((c_x + 15, c_y), (c_x + 50, c_y), color=theme.STATUS_AMBER, thickness=3)
            dpg.draw_circle((c_x, c_y), 3, color=theme.STATUS_AMBER, fill=theme.STATUS_AMBER)

            dpg.draw_rectangle((c_x - 80, c_y - 150), (c_x + 80, c_y - 142), color=theme.ACCENT_TRANS,
                               fill=theme.COLOR_BLACK)
            dpg.draw_triangle((c_x, c_y - 146), (c_x - 5, c_y - 136), (c_x + 5, c_y - 136), fill=theme.STATUS_AMBER,
                              tag=self.yaw_indicator)

            dpg.draw_rectangle((c_x - 155, c_y - 80), (c_x - 147, c_y + 80), color=theme.ACCENT_TRANS,
                               fill=theme.COLOR_BLACK)
            dpg.draw_circle((c_x - 151, c_y), 6, color=theme.STATUS_AMBER, fill=theme.STATUS_AMBER,
                            tag=self.pitch_indicator)

            dpg.draw_rectangle((c_x + 147, c_y - 80), (c_x + 155, c_y + 80), color=theme.ACCENT_TRANS,
                               fill=theme.COLOR_BLACK)
            dpg.draw_circle((c_x + 151, c_y), 6, color=theme.STATUS_AMBER, fill=theme.STATUS_AMBER,
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