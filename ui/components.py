import dearpygui.dearpygui as dpg
from core.data_types import ConnectionStatus, MissionState
import ui.theme as theme
from collections import deque
import numpy as np
import time
import logging

logger = logging.getLogger("MissionControl")

class StatusIndicator:

    @staticmethod
    def set_led(tag, color):
        dpg.configure_item(tag, fill=color)

    @staticmethod
    def set_main_led(status: ConnectionStatus):
        dpg.configure_item("main_status_led", fill=status.value)

    @staticmethod
    def blink_tx():
        dpg.configure_item("tx_led", fill=theme.STATUS_BLUE)

    @staticmethod
    def blink_rx():
        dpg.configure_item("rx_led", fill=theme.STATUS_GREEN)


class TerminalComponent:

    def __init__(self, item_tag, parent_tag, scroll_check_tag="autoscroll_check"):
        self.tag = item_tag
        self.parent_tag = parent_tag
        self.scroll_check_tag = scroll_check_tag
        self.buffer = []
        self.max_lines = 300
        self._needs_update = False
        self._last_scroll_state = True

    def append(self, text: str, level=None):
        self.buffer.append(text)
        if len(self.buffer) > self.max_lines:
            self.buffer.pop(0)
        self._needs_update = True

    def update_ui(self):
        current_scroll_state = dpg.get_value(self.scroll_check_tag)

        toggled_on = current_scroll_state and not self._last_scroll_state
        self._last_scroll_state = current_scroll_state

        if self._needs_update:
            dpg.set_value(self.tag, "\n".join(self.buffer))
            self._needs_update = False

            if current_scroll_state:
                self._do_scroll()

        elif toggled_on:
            self._do_scroll()

    def _do_scroll(self):
        try:
            dpg.set_y_scroll(self.parent_tag, 1000000)
        except:
            pass

    def clear(self):
        self.buffer = []
        dpg.set_value(self.tag, "")
        dpg.set_y_scroll(self.parent_tag, 0.0)
        self._needs_update = False


class FlightDataDisplays:

    @staticmethod
    def update_metrics(alt: float, volt: float, temp: float):
        dpg.set_value("alt_display", f"ALTITUDE: {alt:.1f} m")
        dpg.set_value("temp_display", f"PAYLOAD TEMP: {temp:.1f} °C")
        dpg.set_value("volt_display", f"VOLTAGE: {volt:.2f} V")

        if volt > 0 and volt < 3.4:
            dpg.configure_item("volt_display", color=theme.STATUS_RED)
        else:
            dpg.configure_item("volt_display", color=theme.TEXT_MAIN)

    @staticmethod
    def update_state(state_enum):
        try:
            dpg.set_value("state_display", f"STATE: {state_enum.value}")
        except:
            pass

    @staticmethod
    def update_hardware_tab(frame):
        try:
            dpg.set_value("hw_acc_x", f"ACC X: {frame.accel.x:.0f}")
            dpg.set_value("hw_acc_y", f"ACC Y: {frame.accel.y:.0f}")
            dpg.set_value("hw_acc_z", f"ACC Z: {frame.accel.z:.0f}")
            dpg.set_value("hw_gyr_x", f"GYR X: {frame.gyro.x:.0f}")
            dpg.set_value("hw_gyr_y", f"GYR Y: {frame.gyro.y:.0f}")
            dpg.set_value("hw_gyr_z", f"GYR Z: {frame.gyro.z:.0f}")
            dpg.set_value("hw_mag_x", f"MAG X: {frame.mag.x:.0f}")
            dpg.set_value("hw_mag_y", f"MAG Y: {frame.mag.y:.0f}")
            dpg.set_value("hw_mag_z", f"MAG Z: {frame.mag.z:.0f}")

            dpg.set_value("hw_baro_alt", f"ALT: {frame.altitude:.1f} m")
            dpg.set_value("hw_baro_temp", f"TEMP: {frame.temp:.1f} °C")

            dpg.set_value("hw_gps_fix", f"FIX: {'YES' if frame.gps_fix > 0 else 'NO'}")
            dpg.set_value("hw_gps_sats", f"SATS: {frame.gps_sats}")
            dpg.set_value("hw_gps_lat", f"LAT: {frame.gps_lat:.4f}")
            dpg.set_value("hw_gps_lon", f"LON: {frame.gps_lon:.4f}")
            dpg.set_value("hw_gps_alt", f"G_ALT: {frame.gps_alt:.1f} m")

            dpg.set_value("hw_breakaway", "WIRE: N/A")

            dpg.set_value("hw_pyro1", f"PYRO1: {'FIRE' if frame.pyro1 else 'READY'}")
            dpg.set_value("hw_pyro2", f"PYRO2: {'FIRE' if frame.pyro2 else 'READY'}")

            dpg.set_value("hw_bat_volt", f"VOLT: {frame.voltage:.2f} V (raw ADC, niekalibrowane)")
            dpg.set_value("hw_rssi", f"RSSI: {frame.rssi} dBm")

            dpg.set_value("hw_buzzer", f"BUZZ: {'ON' if frame.buzzer else 'OFF'}")
            dpg.set_value("hw_led_r", f"LED R: {'ON' if frame.led_r else 'OFF'}")
            dpg.set_value("hw_led_g", f"LED G: {'ON' if frame.led_g else 'OFF'}")
            dpg.set_value("hw_led_b", f"LED B: {'ON' if frame.led_b else 'OFF'}")
            dpg.set_value("hw_led_y", f"LED Y: {'ON' if frame.led_y else 'OFF'}")
            dpg.set_value("hw_camera", f"CAM: {'ON' if frame.camera else 'OFF'}")

        except Exception:
            pass


class PayloadManager:

    def __init__(self, plot_tag, max_points=200):
        self.plot_tag = plot_tag
        self.max_points = max_points
        self.times = deque(maxlen=max_points)
        self.temps = deque(maxlen=max_points)
        self.start_time = time.time()

    def reset(self):
        self.times.clear()
        self.temps.clear()
        self.start_time = time.time()
        try:
            dpg.set_value(self.plot_tag, [[], []])
        except Exception:
            pass

    def update(self, temp_val, uv_val=0):
        elapsed = time.time() - self.start_time
        self.times.append(elapsed)
        self.temps.append(temp_val)

        dpg.set_value(self.plot_tag, [list(self.times), list(self.temps)])

        dpg.set_value("big_temp_val", f"{temp_val:.1f} °C")
        dpg.set_value("big_uv_val", f"{int(uv_val)}")

        if len(self.times) > 1:
            dpg.set_axis_limits("temp_x_axis", self.times[0], self.times[-1])
            dpg.set_axis_limits_auto("temp_y_axis")
            dpg.fit_axis_data("temp_y_axis")


class FlightManager:
    def __init__(self, plot_tag, accel_widget=None, max_points=5000):
        self.plot_tag = plot_tag
        self.accel_widget = accel_widget
        self.times = deque(maxlen=max_points)
        self.altitudes = deque(maxlen=max_points)
        self.start_time = time.time()

    def reset(self):
        self.times.clear()
        self.altitudes.clear()
        self.start_time = time.time()
        dpg.set_value(self.plot_tag, [[], []])

    def update(self, altitude, voltage, state_name, accel):
        elapsed = time.time() - self.start_time
        self.times.append(elapsed)
        self.altitudes.append(altitude)

        dpg.set_value(self.plot_tag, [list(self.times), list(self.altitudes)])

        dpg.set_value("big_flight_alt_val", f"{altitude:.1f} m")
        dpg.set_value("big_flight_volt_val", f"{voltage:.2f} V")
        dpg.set_value("big_flight_state_val", f"{state_name}")

        if self.accel_widget:
            self.accel_widget.update(accel.x, accel.y, accel.z)


class GPSManager:
    def __init__(self):
        self.lats = []
        self.lons = []

    def reset(self):
        self.lats.clear()
        self.lons.clear()
        try:
            dpg.set_value("gps_path_series", [[], []])
            dpg.set_value("gps_current_series", [[], []])
        except Exception:
            pass

    def update(self, lat: float, lon: float, fix: int):
        if fix > 0 and lat != 0.0 and lon != 0.0:

            if self.lats and (abs(self.lats[-1] - lat) > 0.01 or abs(self.lons[-1] - lon) > 0.01):
                self.lats.clear()
                self.lons.clear()

            if not self.lats or (abs(self.lats[-1] - lat) > 1e-6 or abs(self.lons[-1] - lon) > 1e-6):
                self.lats.append(lat)
                self.lons.append(lon)

                dpg.set_value("gps_path_series", [self.lons, self.lats])
                dpg.set_value("gps_current_series", [[lon], [lat]])

                if len(self.lats) < 2:
                    dpg.set_axis_limits("gps_x_axis", lon - 0.005, lon + 0.005)
                    dpg.set_axis_limits("gps_y_axis", lat - 0.005, lat + 0.005)
                else:
                    dpg.set_axis_limits_auto("gps_x_axis")
                    dpg.set_axis_limits_auto("gps_y_axis")
                    dpg.fit_axis_data("gps_x_axis")
                    dpg.fit_axis_data("gps_y_axis")
