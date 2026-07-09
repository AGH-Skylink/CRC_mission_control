import dearpygui.dearpygui as dpg
import time
from core.serial_manager import SerialManager
from core.telemetry import TelemetryParser
from core.logger import MissionLogger
from core.data_types import ConnectionStatus, MissionState
from ui.layout import MissionControlLayout
from ui.components import StatusIndicator, TerminalComponent, FlightDataDisplays, PayloadManager, FlightManager, GPSManager
import ui.theme as theme


class MissionControlApp:
    def __init__(self):
        self.serial = SerialManager()
        self.parser = TelemetryParser()
        self.logger = MissionLogger()
        self.gps_mgr = GPSManager()
        self.tx_timer = 0.0
        self.rx_timer = 0.0

        self.layout = MissionControlLayout()
        self.terminal = None
        self.payload_mgr = None
        self.flight_mgr = None
        self._prev_flight_mission_state = None  # do wykrywania startu (IDLE -> cokolwiek innego)

        self.raw_feed_buffer = []

        self.terminal_raw = TerminalComponent("raw_telemetry_feed", "raw_feed_container")

        self.replay_thread = None
        self.replay_running = False
        self.replay_paused = False
        self.selected_replay_file = None

        dpg.create_context()
        theme.apply_skylink_theme()
        theme.setup_fonts()

    def setup(self):
        self.logger.info("Initializing UI Layout...")
        dpg.create_viewport(title='FST AGH - Mission Control v2', width=1300, height=800)
        dpg.set_viewport_min_width(1200)
        dpg.set_viewport_min_height(700)
        self.layout.create_layout()
        self.payload_mgr = PayloadManager("temp_plot_series")
        self.flight_mgr = FlightManager("flight_alt_plot_series", accel_widget=self.layout.accel_vector)

        self.terminal = TerminalComponent(
            self.layout.terminal_id,
            "terminal_container",
            "autoscroll_check"
        )

        self.terminal_raw = TerminalComponent(
            "raw_telemetry_feed",
            "raw_feed_container",
            "raw_autoscroll_check"
        )

        self.terminal_cmd = TerminalComponent(
            "command_console",
            "command_console_container",
            "cmd_autoscroll_check"
        )

        self.sequences = {
            "Pre-flight Hardware Test": [("ARM", 1.0), ("TEST_BUZZER", 2.0), ("TEST_SERVOS", 2.0), ("DISARM", 0.0)],
            "Abort & Safing Procedure": [("ABORT", 0.5), ("DISARM", 0.0)],
            "Full Recovery Test": [("ARM", 0.5), ("DEPLOY_CHUTE", 3.0), ("DISARM", 0.0)]
        }

        self.logger.add_ui_handler(self.terminal.append)

        dpg.configure_item("scan_btn", callback=self._on_scan)
        dpg.configure_item("connect_btn", callback=self._on_connect)
        dpg.configure_item("send_btn", callback=self._on_send)
        dpg.configure_item("cmd_input", callback=self._on_send, on_enter=True)

        dpg.configure_item("clear_raw_btn", callback=self.terminal_raw.clear)
        dpg.configure_item("clear_cmd_btn", callback=self.terminal_cmd.clear)

        dpg.configure_item("replay_play_btn", callback=self._on_replay_play)
        dpg.configure_item("replay_pause_btn", callback=self._on_replay_pause)
        dpg.configure_item("replay_stop_btn", callback=self._on_replay_stop)

        dpg.configure_item("replay_select_file_btn", callback=lambda: dpg.show_item("replay_file_dialog"))
        dpg.configure_item("replay_file_dialog", callback=self._on_file_selected)

        dpg.configure_item("arm_btn", callback=lambda: self._send_cmd("ARM"))
        dpg.configure_item("disarm_btn", callback=lambda: self._send_cmd("DISARM"))
        dpg.configure_item("reset_btn", callback=lambda: self._send_cmd("RESET"))
        dpg.configure_item("abort_btn", callback=lambda: self._send_cmd("ABORT"))

        dpg.configure_item("settings_btn", callback=lambda: dpg.configure_item("settings_window", show=True))

        dpg.configure_item("seq_combo", items=list(self.sequences.keys()), callback=self._on_sequence_select)
        dpg.configure_item("seq_send_btn", callback=self._run_sequence)

        dpg.configure_item("deploy_btn", callback=lambda: self._send_cmd("DEPLOY_CHUTE"))

        # dpg.configure_item("sched_start_btn", callback=lambda: self._send_cmd("START_SEQ"))
        # dpg.configure_item("sched_clear_btn", callback=lambda: self._send_cmd("CLEAR_SEQ"))

        dpg.configure_item("buzzer_test_btn", callback=lambda: self._send_cmd("TEST_BUZZER"))
        dpg.configure_item("servo_test_btn", callback=lambda: self._send_cmd("TEST_SERVOS"))

        def refocus_callback():
            dpg.focus_item("cmd_input")

        dpg.configure_item("autoscroll_check", callback=refocus_callback)
        dpg.configure_item("raw_autoscroll_check", callback=refocus_callback)
        dpg.configure_item("cmd_autoscroll_check", callback=refocus_callback)

    def _on_scan(self):
        ports = self.serial.scan_ports()
        dpg.configure_item("port_combo", items=ports)
        self.logger.info(f"Scanned ports: {ports}")

    def _on_connect(self):
        if self.serial.is_running:
            self.serial.disconnect()
            self.logger.warning("Disconnected from port")
        else:
            port = dpg.get_value("port_combo")
            baudrate_str = dpg.get_value("stg_baudrate")
            baudrate = int(baudrate_str) if baudrate_str else 115200

            if port and self.serial.connect(port, baudrate):
                self.logger.info(f"Connected to {port} at {baudrate} bps")
            else:
                self.logger.error("Failed to connect!")


    def _on_send(self):
        cmd = dpg.get_value("cmd_input")
        if not cmd.strip():
            return
        if self._send_cmd(cmd):
            dpg.set_value("cmd_input", "")
        dpg.focus_item("cmd_input")

    def _send_cmd(self, cmd):
        if self.serial.send_data(cmd):
            StatusIndicator.set_led("tx_led", theme.STATUS_BLUE)
            self.tx_timer = time.time() + 0.1

            self.logger.info(f"Sent: {cmd}")
            self.terminal_cmd.append(f"TX > {cmd}")
            return True
        return False

    def _log_raw(self, text):
        current_val = dpg.get_value("raw_telemetry_feed")
        lines = (current_val + "\n" + text).split('\n')
        dpg.set_value("raw_telemetry_feed", "\n".join(lines[-50:]))

        if dpg.get_value("raw_autoscroll_check"):
            try:
                dpg.set_y_scroll("raw_feed_container", -1.0)
            except:
                pass

    def _append_to_feed(self, text):
        self.raw_feed_buffer.append(text)

        if len(self.raw_feed_buffer) > 100:
            self.raw_feed_buffer.pop(0)

        try:
            dpg.set_value("raw_telemetry_feed", "\n".join(self.raw_feed_buffer))
            if dpg.get_value("autoscroll_check"):
                dpg.set_y_scroll("raw_telemetry_container", -1.0)
        except Exception:
            pass

    def run(self):
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window("Primary Window", True)

        while dpg.is_dearpygui_running():
            now = time.time()
            lines_processed = 0
            while not self.serial.raw_queue.empty() and lines_processed < 20:
                raw_bytes = self.serial.raw_queue.get()
                lines_processed += 1

                StatusIndicator.set_led("rx_led", theme.STATUS_GREEN)
                self.rx_timer = now + 0.1

                raw_hex = raw_bytes.hex(' ').upper()

                self.logger.log_raw_frame(raw_hex)
                self.terminal_raw.append(f"RX > {raw_hex}")

                frame = self.parser.parse_frame(raw_bytes)
                if frame:
                    self.logger.log_telemetry(frame)

                    self.layout.navball.update(frame.pitch, frame.roll, frame.yaw)
                    FlightDataDisplays.update_state(frame.state)
                    FlightDataDisplays.update_metrics(frame.altitude, frame.voltage, frame.temp)

                    FlightDataDisplays.update_hardware_tab(frame)

                    if self.payload_mgr:
                        self.payload_mgr.update(frame.temp, 0.0)

                    if self.flight_mgr:
                        # Wykres wysokosci ma STALE osie 0-100s / 0-700m
                        # (patrz ui/layout.py) skalibrowane pod czas TRWANIA
                        # LOTU, a nie pod czas dzialania aplikacji. Bez tego
                        # resetu zegar FlightManager liczylby od uruchomienia
                        # Mission Control (SCAN/CONNECT moga zajac >100s),
                        # wiec punkty ladowalyby poza widocznym zakresem osi
                        # X i wykres wygladalby na pusty mimo poprawnych
                        # danych. Resetujemy zegar w momencie wykrycia startu
                        # (przejscie z IDLE na dowolny inny stan).
                        if self._prev_flight_mission_state == MissionState.IDLE and frame.state != MissionState.IDLE:
                            self.flight_mgr.reset()
                        self._prev_flight_mission_state = frame.state

                        self.flight_mgr.update(frame.altitude, frame.voltage, frame.state.name, frame.accel)

                    self.gps_mgr.update(frame.gps_lat, frame.gps_lon, frame.gps_fix)

            self.terminal.update_ui()
            self.terminal_raw.update_ui()
            self.terminal_cmd.update_ui()
            self._update_indicators(now)

            current_status = self.parser.get_connection_status()
            StatusIndicator.set_main_led(current_status)
            dpg.set_value("bitrate_text", f"{self.serial.bitrate:.1f} kb/s")

            dpg.render_dearpygui_frame()

        self.logger.info("Mission Control Session Ended")
        self.serial.disconnect()
        dpg.destroy_context()

    def _update_indicators(self, now):
        status = self.parser.get_connection_status()

        if status == ConnectionStatus.DROPPED_FRAMES:
            is_on = (int(now * 5) % 2) == 0
            color = theme.STATUS_AMBER if is_on else theme.COLOR_BLACK
            StatusIndicator.set_led("main_status_led", color)
        else:
            StatusIndicator.set_main_led(status)

        if now > self.tx_timer:
            StatusIndicator.set_led("tx_led", theme.COLOR_BLACK)
        if now > self.rx_timer:
            StatusIndicator.set_led("rx_led", theme.COLOR_BLACK)

    def _log_raw(self, text):
        current_val = dpg.get_value("raw_telemetry_feed")
        lines = (current_val + "\n" + text).split('\n')
        dpg.set_value("raw_telemetry_feed", "\n".join(lines[-50:]))

        if dpg.get_value("raw_autoscroll_check"):
            try:
                dpg.set_y_scroll("raw_feed_container", dpg.get_y_scroll_max("raw_feed_container"))
            except:
                pass

    def _log_command(self, text):
        current_val = dpg.get_value("command_console")
        dpg.set_value("command_console", current_val + "\n" + text)

        if dpg.get_value("cmd_autoscroll_check"):
            try:
                dpg.set_y_scroll("command_console_container", dpg.get_y_scroll_max("command_console_container"))
            except:
                pass

    def _on_replay_play(self):
        if self.replay_paused:
            self.replay_paused = False
            self.logger.info("Wznowiono odtwarzanie logów.")
            return

        if self.replay_running:
            return

        if not self.selected_replay_file:
            self.logger.error("Nie wybrano pliku! Kliknij 'CHOOSE LOG FILE' przed uruchomieniem.")
            return

        import threading
        self.replay_running = True
        self.replay_paused = False
        self.replay_thread = threading.Thread(target=self._replay_loop, args=(self.selected_replay_file,), daemon=True)
        self.replay_thread.start()
        self.logger.info("Uruchomiono symulację lotu z pliku zewnętrznego.")

    def _on_replay_pause(self):
        if self.replay_running:
            self.replay_paused = True
            self.logger.warning("Wstrzymano odtwarzanie logów.")

    def _on_replay_stop(self):
        self.replay_running = False
        self.replay_paused = False
        self.logger.error("Zatrzymano odtwarzanie. Reset kolejki.")

    def _replay_loop(self, file_path):
        clean_lines = []
        try:
            import csv
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                first_line = f.readline()
                f.seek(0)

                if ',' in first_line:
                    reader = csv.reader(f)
                    header = next(reader, None)
                    if header and not header[0].replace('.', '', 1).isdigit() and "timestamp" not in header[0]:
                        f.seek(0)
                        reader = csv.reader(f)

                    for row in reader:
                        if len(row) >= 2:
                            clean_lines.append(row[1].strip())
                        elif len(row) == 1:
                            clean_lines.append(row[0].strip())

                else:
                    for line in f:
                        line = line.strip()
                        if not line: continue
                        if "RX > " in line: line = line.split("RX > ")[1]
                        clean_lines.append(line)

        except Exception as e:
            self.logger.error(f"Krytyczny błąd odczytu pliku: {e}")
            self.replay_running = False
            return

        for line in clean_lines:
            while self.replay_paused and self.replay_running:
                time.sleep(0.1)
            if not self.replay_running:
                break

            try:
                hex_str = line.replace(" ", "")
                raw_bytes = bytes.fromhex(hex_str)

                self.serial.raw_queue.put(raw_bytes)

                speed = dpg.get_value("replay_speed_slider")
                time.sleep(0.05 / max(0.1, speed))

            except Exception as e:
                self.logger.error(f"Błąd dekodowania ramki '{line}': {e}")

        self.replay_running = False
        self.logger.info("Zakończono odtwarzanie historycznego logu misji.")


    def _on_file_selected(self, sender, app_data):
        file_path = app_data.get("file_path_name", "")
        file_name = app_data.get("file_name", "")

        if file_path:
            self.selected_replay_file = file_path
            dpg.set_value("replay_file_path_text", f"LOADED: {file_name}\nFull path: {file_path}")
            dpg.configure_item("replay_file_path_text", color=theme.STATUS_GREEN)
            self.logger.info(f"Załadowano plik repliki lotu: {file_name}")

    def _on_sequence_select(self, sender, app_data):
        seq_name = app_data
        if seq_name in self.sequences:
            steps_text = f"Sequence steps for '{seq_name}':\n"
            for cmd, delay in self.sequences[seq_name]:
                steps_text += f" > {cmd} (wait {delay}s)\n"
            dpg.set_value("seq_preview_text", steps_text)

    def _run_sequence(self):
        seq_name = dpg.get_value("seq_combo")
        if not seq_name or seq_name not in self.sequences:
            self.logger.warning("No valid sequence selected.")
            return

        def execute_macro():
            self.logger.info(f"STARTING MACRO: {seq_name}")
            for cmd, delay in self.sequences[seq_name]:
                self._send_cmd(cmd)
                time.sleep(delay)
            self.logger.info(f"MACRO FINISHED: {seq_name}")

        import threading
        threading.Thread(target=execute_macro, daemon=True).start()


if __name__ == "__main__":
    app = MissionControlApp()
    app.setup()
    app.run()