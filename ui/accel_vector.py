import math
import dearpygui.dearpygui as dpg
import ui.theme as theme


class AccelVectorWidget:
    LSB_PER_G = 256.0

    def __init__(self, parent_tag, width=300, height=300):
        self.width = width
        self.height = height
        self.cx = width / 2
        self.cy = height * 0.7
        self.axis_len = 80       # dlugosc osi referencyjnych w pikselach (1g)
        self.max_vec_len = 170   # maksymalna dlugosc rysowanego wektora

        self.vector_tag = dpg.generate_uuid()
        self.tip_dot_tag = dpg.generate_uuid()
        self.label_tag = dpg.generate_uuid()

        self._build_ui(parent_tag)

    def _iso_project(self, x, y, z):
        cos30 = math.cos(math.radians(30))
        sin30 = math.sin(math.radians(30))
        sx = self.cx + (x - z) * cos30
        sy = self.cy - y - (x + z) * sin30
        return sx, sy

    def _draw_floor_grid(self, half_extent_units, step_units, unit_px):
        grid_color = (60, 60, 60)
        n = int(half_extent_units / step_units)
        for i in range(-n, n + 1):
            x = i * step_units * unit_px
            p1 = self._iso_project(x, 0, -half_extent_units * unit_px)
            p2 = self._iso_project(x, 0, half_extent_units * unit_px)
            dpg.draw_line(p1, p2, color=grid_color, thickness=1)

            z = i * step_units * unit_px
            p3 = self._iso_project(-half_extent_units * unit_px, 0, z)
            p4 = self._iso_project(half_extent_units * unit_px, 0, z)
            dpg.draw_line(p3, p4, color=grid_color, thickness=1)

    def _draw_reference_ring(self, radius_px, color):
        pts = []
        segments = 40
        for i in range(segments + 1):
            ang = 2 * math.pi * i / segments
            x = radius_px * math.cos(ang)
            z = radius_px * math.sin(ang)
            pts.append(self._iso_project(x, 0, z))
        for p1, p2 in zip(pts, pts[1:]):
            dpg.draw_line(p1, p2, color=color, thickness=1)

    def _build_ui(self, parent_tag):
        with dpg.drawlist(width=self.width, height=self.height, parent=parent_tag):
            dpg.draw_rectangle((0, 0), (self.width, self.height), color=theme.COLOR_BLACK, fill=theme.COLOR_BLACK)

            unit_px = self.axis_len
            self._draw_floor_grid(half_extent_units=2, step_units=1, unit_px=unit_px / 2)
            self._draw_reference_ring(unit_px, theme.ACCENT_TRANS[:3] if len(theme.ACCENT_TRANS) == 4 else theme.ACCENT_TRANS)
            self._draw_reference_ring(unit_px * 2, (50, 50, 50))

            origin = self._iso_project(0, 0, 0)

            x_end = self._iso_project(self.axis_len, 0, 0)
            y_end = self._iso_project(0, self.axis_len, 0)
            z_end = self._iso_project(0, 0, self.axis_len)

            dpg.draw_arrow(x_end, origin, color=(180, 70, 70), thickness=1, size=6)
            dpg.draw_arrow(y_end, origin, color=(70, 160, 70), thickness=1, size=6)
            dpg.draw_arrow(z_end, origin, color=(70, 110, 200), thickness=1, size=6)

            dpg.draw_text((x_end[0] + 4, x_end[1]), "X", color=(220, 100, 100), size=13)
            dpg.draw_text((y_end[0] + 4, y_end[1] - 14), "Y", color=(100, 220, 100), size=13)
            dpg.draw_text((z_end[0] - 14, z_end[1]), "Z", color=(100, 150, 230), size=13)

            dpg.draw_circle(origin, 3, color=theme.TEXT_NORMAL, fill=theme.TEXT_NORMAL)

            dpg.draw_arrow(origin, origin, color=theme.STATUS_AMBER, thickness=6, size=18, tag=self.vector_tag)
            dpg.draw_circle(origin, 8, color=theme.STATUS_AMBER, fill=theme.STATUS_AMBER, tag=self.tip_dot_tag)

            dpg.draw_text(
                (6, self.height - 34),
                "a = (0, 0, 0)\n|a| = 0.00 g",
                color=theme.STATUS_AMBER, size=13, tag=self.label_tag,
            )

    def update(self, ax: float, ay: float, az: float):
        mag_raw = math.sqrt(ax * ax + ay * ay + az * az)
        mag_g = mag_raw / self.LSB_PER_G

        if mag_raw > 1e-6:
            length_px = min((mag_raw / self.LSB_PER_G) * self.axis_len, self.max_vec_len)
            k = length_px / mag_raw
        else:
            k = 0.0

        origin = self._iso_project(0, 0, 0)
        NOSE_SIGN = -1.0
        tip = self._iso_project(ay * k, (NOSE_SIGN * ax) * k, az * k)

        dpg.configure_item(self.vector_tag, p1=origin, p2=tip)
        dpg.configure_item(self.tip_dot_tag, center=tip)
        dpg.configure_item(
            self.label_tag,
            text=f"a = ({ax:.0f}, {ay:.0f}, {az:.0f})\n|a| = {mag_g:.2f} g",
        )
