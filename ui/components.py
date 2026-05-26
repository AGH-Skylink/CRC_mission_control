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


class PayloadManager:

    def __init__(self, plot_tag, max_points=200):
        self.plot_tag = plot_tag
        self.max_points = max_points
        self.times = deque(maxlen=max_points)
        self.temps = deque(maxlen=max_points)
        self.start_time = time.time()

    def update(self, temp_val, uv_val=0):
        elapsed = time.time() - self.start_time
        self.times.append(elapsed)
        self.temps.append(temp_val)

        dpg.set_value(self.plot_tag, [list(self.times), list(self.temps)])

        dpg.set_value("big_temp_val", f"{temp_val:.1f} °C")
        dpg.set_value("big_uv_val", f"{int(uv_val)}")

        if len(self.times) > 1:
            dpg.set_axis_limits("temp_x_axis", self.times[0], self.times[-1])