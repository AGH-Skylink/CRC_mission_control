import dearpygui.dearpygui as dpg
from ui.navball import NavballWidget
from ui.accel_vector import AccelVectorWidget
import ui.theme as theme


class MissionControlLayout:
    def __init__(self):
        self.navball = None
        self.accel_vector = None
        self.terminal_id = "telemetry_feed_terminal"

    def create_layout(self):
        # Główny kontener Viewportu - wyłączamy scrollbar dla całego okna
        with dpg.window(tag="Primary Window", no_title_bar=True, no_move=True,
                        no_resize=True, no_scrollbar=True):
            # --- 1. TOP BAR (Stała wysokość: 60px) ---
            with dpg.child_window(height=60, border=False, no_scrollbar=True):
                with dpg.group(horizontal=True):
                    dpg.add_text("0.0 kb/s", tag="bitrate_text", color=theme.ACCENT_PRIMARY)
                    dpg.add_spacer(width=20)
                    dpg.add_button(label="SCAN", width=80, tag="scan_btn")
                    dpg.add_combo(items=[], label="", width=150, tag="port_combo")
                    with dpg.drawlist(width=30, height=30):
                        dpg.draw_circle((15, 15), 10, color=theme.ACCENT_TRANS, fill=theme.COLOR_BLACK,
                                        tag="main_status_led")
                    dpg.add_button(label="OPEN | CLOSE", width=120, tag="connect_btn")
                    dpg.add_button(label="STG", width=40, tag="settings_btn")
                    dpg.add_spacer(width=20)
                    with dpg.group():
                        with dpg.group(horizontal=True):
                            dpg.add_text("TX", color=theme.TEXT_NORMAL)
                            with dpg.drawlist(width=15, height=15):
                                dpg.draw_circle((7, 7), 5, fill=theme.COLOR_BLACK, tag="tx_led")
                        with dpg.group(horizontal=True):
                            dpg.add_text("RX", color=theme.TEXT_NORMAL)
                            with dpg.drawlist(width=15, height=15):
                                dpg.draw_circle((7, 7), 5, fill=theme.COLOR_BLACK, tag="rx_led")

            dpg.add_separator()

            # --- 2. ŚRODKOWY OBSZAR ROBOCZY (Dynamiczna wysokość) ---
            with dpg.child_window(height=-110, border=False, tag="main_content_area"):
                with dpg.tab_bar():
                    # KARTA: COMMUNICATION
                    # ui/layout.py - Fragment zakładki COMMUNICATION
                    with dpg.tab(label="COMMUNICATION"):
                        with dpg.group(horizontal=True):
                            # Lewa kolumna: Terminale
                            with dpg.child_window(width=-400, border=True):
                                # RAW TELEMETRY FEED
                                with dpg.group(horizontal=True):
                                    dpg.add_text("TELEMETRY FEED (RAW)", color=theme.ACCENT_PRIMARY)
                                    dpg.add_spacer(width=20)
                                    dpg.add_checkbox(label="AUTO", default_value=True, tag="raw_autoscroll_check")
                                    dpg.add_button(label="CLEAR", tag="clear_raw_btn", small=True)

                                with dpg.child_window(height=350, border=True, tag="raw_feed_container"):
                                    dpg.add_text("", tag="raw_telemetry_feed")

                                dpg.add_spacer(height=10)
                                dpg.add_separator()

                                # COMMAND CONSOLE
                                with dpg.group(horizontal=True):
                                    dpg.add_text("COMMAND CONSOLE", color=theme.STATUS_BLUE)
                                    dpg.add_spacer(width=35)
                                    dpg.add_checkbox(label="AUTO", default_value=True, tag="cmd_autoscroll_check")
                                    dpg.add_button(label="CLEAR", tag="clear_cmd_btn", small=True)

                                with dpg.child_window(height=-1, border=True, tag="command_console_container"):
                                    dpg.add_text("", tag="command_console")

                            # Prawa kolumna: Navball i Wskaźniki
                            with dpg.child_window(width=380, border=True):
                                nav_container = dpg.add_child_window(height=350, border=False)
                                self.navball = NavballWidget(nav_container)
                                dpg.add_separator()
                                dpg.add_text("STATE: IDLE", tag="state_display")
                                dpg.add_text("ALTITUDE: 0.0 m", tag="alt_display")
                                dpg.add_text("PAYLOAD TEMP: 0.0 °C", tag="temp_display")
                                dpg.add_text("VOLTAGE: 0.0 V", tag="volt_display")

                    # KARTA: PAYLOAD
                    with dpg.tab(label="PAYLOAD"):
                        dpg.add_spacer(height=10)
                        dpg.add_text("ALGAE BIOLOGICAL PAYLOAD MONITOR", indent=550, color=theme.ACCENT_PRIMARY)
                        with dpg.group(horizontal=True):
                            with dpg.child_window(width=400, height=150, border=False):
                                dpg.add_text("CURRENT TEMP", color=theme.TEXT_NORMAL)
                                dpg.add_text("20.0 °C", tag="big_temp_val", color=theme.STATUS_AMBER)
                                dpg.bind_item_font("big_temp_val", "big_payload_font")
                            with dpg.child_window(width=400, height=150, border=False):
                                dpg.add_text("UV INTENSITY", color=theme.TEXT_NORMAL)
                                dpg.add_text("0", tag="big_uv_val", color=theme.STATUS_BLUE)
                                dpg.bind_item_font("big_uv_val", "big_payload_font")
                        with dpg.plot(height=-1, width=-1):
                            dpg.add_plot_legend()
                            dpg.add_plot_axis(dpg.mvXAxis, label="Time (s)", tag="temp_x_axis")
                            y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="Temp (°C)", tag="temp_y_axis")
                            dpg.add_line_series([], [], label="Temp Trend", parent=y_axis, tag="temp_plot_series")

                    # KARTA: FLIGHT (wysokosc w czasie, wektor przyspieszenia 3D,
                    # napiecie, stan lotu)
                    with dpg.tab(label="FLIGHT"):
                        dpg.add_spacer(height=10)
                        dpg.add_text("FLIGHT OVERVIEW", indent=550, color=theme.ACCENT_PRIMARY)

                        with dpg.group(horizontal=True):
                            with dpg.child_window(width=260, height=150, border=False):
                                dpg.add_text("ALTITUDE", color=theme.TEXT_NORMAL)
                                dpg.add_text("0.0 m", tag="big_flight_alt_val", color=theme.STATUS_AMBER)
                                dpg.bind_item_font("big_flight_alt_val", "big_payload_font")
                            with dpg.child_window(width=260, height=150, border=False):
                                dpg.add_text("BATTERY VOLTAGE", color=theme.TEXT_NORMAL)
                                dpg.add_text("0.00 V", tag="big_flight_volt_val", color=theme.STATUS_BLUE)
                                dpg.bind_item_font("big_flight_volt_val", "big_payload_font")
                            with dpg.child_window(width=260, height=150, border=False):
                                dpg.add_text("FLIGHT STATE", color=theme.TEXT_NORMAL)
                                dpg.add_text("IDLE", tag="big_flight_state_val", color=theme.STATUS_GREEN)
                                dpg.bind_item_font("big_flight_state_val", "big_payload_font")

                        dpg.add_spacer(height=10)

                        with dpg.group(horizontal=True):
                            # Wykres wysokosci w czasie - STALE osie (nie
                            # przewijajacy sie jak w PAYLOAD), dopasowane do
                            # profilu lotu z raportu koncowego (OpenRocket
                            # sim: apogeum ~533 m, calkowity czas lotu ~91.8 s)
                            with dpg.child_window(width=-330, height=-1, border=True):
                                dpg.add_text("ALTITUDE OVER TIME", color=theme.ACCENT_PRIMARY)
                                with dpg.plot(height=-1, width=-1):
                                    dpg.add_plot_legend()
                                    dpg.add_plot_axis(dpg.mvXAxis, label="Time (s)", tag="flight_alt_x_axis")
                                    dpg.set_axis_limits("flight_alt_x_axis", 0, 100)
                                    alt_y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="Altitude (m)", tag="flight_alt_y_axis")
                                    dpg.set_axis_limits(alt_y_axis, 0, 700)
                                    dpg.add_line_series([], [], label="Altitude", parent=alt_y_axis, tag="flight_alt_plot_series")

                            # Wektor przyspieszenia 3D (rzut izometryczny)
                            with dpg.child_window(width=320, height=-1, border=True):
                                dpg.add_text("ACCELERATION VECTOR (3D)", color=theme.ACCENT_PRIMARY)
                                accel_container = dpg.add_child_window(height=-1, border=False)
                                self.accel_vector = AccelVectorWidget(accel_container)

                    # KARTA: HARDWARE
                    with dpg.tab(label="HARDWARE"):
                        with dpg.child_window(width=-1, height=-1, border=False, horizontal_scrollbar=True):
                            with dpg.group(horizontal=True):
                                dpg.add_text("Crc 2026 Rocket Hardware", color=theme.ACCENT_PRIMARY)
                                dpg.add_spacer(width=50)
                                dpg.add_button(label="Maintenance", width=120)
                                dpg.add_button(label="Snapshot", width=100)

                            dpg.add_spacer(height=10)
                            with dpg.group(horizontal=True):
                                panel_w, panel_h = 125, 230

                                # 1. Panel IMU (Akcelerometr i Żyroskop)
                                with dpg.child_window(width=panel_w, height=panel_h, border=True):
                                    dpg.add_text("IMU_MPU9250", color=theme.TEXT_NORMAL)
                                    dpg.add_separator()
                                    dpg.add_text("ACC X: --", tag="hw_acc_x")
                                    dpg.add_text("ACC Y: --", tag="hw_acc_y")
                                    dpg.add_text("ACC Z: --", tag="hw_acc_z")
                                    dpg.add_spacer(height=5)
                                    dpg.add_text("GYR X: --", tag="hw_gyr_x")
                                    dpg.add_text("GYR Y: --", tag="hw_gyr_y")
                                    dpg.add_text("GYR Z: --", tag="hw_gyr_z")
                                    dpg.add_spacer(height=5)
                                    dpg.add_text("MAG X: --", tag="hw_mag_x")
                                    dpg.add_text("MAG Y: --", tag="hw_mag_y")
                                    dpg.add_text("MAG Z: --", tag="hw_mag_z")

                                # 2. Panel Barometru
                                with dpg.child_window(width=panel_w, height=panel_h, border=True):
                                    dpg.add_text("BARO_BMP280", color=theme.TEXT_NORMAL)
                                    dpg.add_separator()
                                    dpg.add_text("ALT: -- m", tag="hw_baro_alt")
                                    dpg.add_text("TEMP: -- °C", tag="hw_baro_temp")

                                # 3. Panel GPS
                                with dpg.child_window(width=panel_w + 15, height=panel_h, border=True):
                                    dpg.add_text("GPS_GP02", color=theme.TEXT_NORMAL)
                                    dpg.add_separator()
                                    dpg.add_text("FIX: --", tag="hw_gps_fix")
                                    dpg.add_text("SATS: --", tag="hw_gps_sats")
                                    dpg.add_text("LAT: --", tag="hw_gps_lat")
                                    dpg.add_text("LON: --", tag="hw_gps_lon")
                                    dpg.add_text("G_ALT: -- m", tag="hw_gps_alt")

                                # 4. Zastąpiony panel BODY_STRESS -> BREAKAWAY WIRE
                                with dpg.child_window(width=panel_w, height=panel_h, border=True):
                                    dpg.add_text("BREAKAWAY", color=theme.TEXT_NORMAL)
                                    dpg.add_separator()
                                    # UWAGA: firmware GS obecnie NIE wysyla stanu zerwania
                                    # linki w telemetrii (brak tego bitu w ramce) - domyslnie
                                    # "N/A", zeby nie sugerowac realnego odczytu.
                                    dpg.add_text("WIRE: N/A", tag="hw_breakaway")

                                # 5. Kontrola mechanizmów (Lotki aerodynamiczne)
                                with dpg.child_window(width=panel_w, height=panel_h, border=True):
                                    dpg.add_text("AERO_FINS", color=theme.TEXT_NORMAL)
                                    dpg.add_spacer(height=10)
                                    dpg.add_text("0", indent=55)
                                    dpg.add_input_text(width=-1, default_value="--")
                                    dpg.add_button(label="SET", width=-1)
                                    dpg.add_spacer(height=5)
                                    dpg.add_button(label="OPEN", width=-1)
                                    dpg.add_button(label="CLOSE", width=-1)

                                # 6. System Odzyskiwania (Spadochrony)
                                with dpg.child_window(width=panel_w, height=panel_h, border=True):
                                    dpg.add_text("RECOVERY_SYS", color=theme.TEXT_NORMAL)
                                    dpg.add_separator()
                                    dpg.add_text("PYRO1: OFF", tag="hw_pyro1")
                                    dpg.add_text("PYRO2: OFF", tag="hw_pyro2")
                                    dpg.add_spacer(height=25)
                                    dpg.add_button(label="ARM", width=-1)
                                    dpg.add_button(label="DISARM", width=-1)

                                # 7. Zasilanie i parametry sygnału radiowego
                                with dpg.child_window(width=panel_w, height=panel_h, border=True):
                                    dpg.add_text("BATTERY", color=theme.TEXT_NORMAL)
                                    dpg.add_separator()
                                    dpg.add_text("VOLT: -- V", tag="hw_bat_volt")
                                    dpg.add_text("RSSI: -- dBm", tag="hw_rssi")

                                # 8. Karta SD Loggera pokładowego
                                with dpg.child_window(width=panel_w, height=panel_h, border=True):
                                    dpg.add_text("SD_LOGGER", color=theme.TEXT_NORMAL)
                                    dpg.add_spacer(height=25)
                                    dpg.add_button(label="START", width=-1)
                                    dpg.add_button(label="STOP", width=-1)
                                    dpg.add_button(label="ERASE", width=-1)

                                # 9. Buzzer i Sygnalizacja LED
                                with dpg.child_window(width=panel_w, height=panel_h, border=True):
                                    dpg.add_text("BUZZER_LEDS", color=theme.TEXT_NORMAL)
                                    dpg.add_separator()
                                    dpg.add_text("BUZZ: OFF", tag="hw_buzzer")
                                    dpg.add_text("LED R: OFF", tag="hw_led_r")
                                    dpg.add_text("LED G: OFF", tag="hw_led_g")
                                    dpg.add_text("LED B: OFF", tag="hw_led_b")
                                    dpg.add_text("LED Y: OFF", tag="hw_led_y")
                                    dpg.add_text("CAM: OFF", tag="hw_camera")

                                # # 10. Harmonogram lotu
                                # with dpg.child_window(width=panel_w + 15, height=panel_h, border=True):
                                #     dpg.add_text("FLIGHT_SCHED", color=theme.TEXT_NORMAL)
                                #     dpg.add_text("Seq State Unk", color=theme.TEXT_NORMAL, wrap=120)
                                #     dpg.add_spacer(height=15)
                                #     with dpg.group(horizontal=True):
                                #         dpg.add_button(label="START", width=60, tag="sched_start_btn")
                                #         dpg.add_button(label="CLEAR", width=60, tag="sched_clear_btn")

                    # KARTA: SEQUENCES
                    with dpg.tab(label="SEQUENCES"):
                        dpg.add_spacer(height=10)
                        with dpg.group(horizontal=True):
                            dpg.add_text("Sequences", indent=250)
                            dpg.add_combo(items=[], width=300, tag="seq_combo")
                            dpg.add_button(label="NEW", width=80)
                            dpg.add_button(label="EDIT", width=80)
                            dpg.add_button(label="SEND", width=80, tag="seq_send_btn")
                        dpg.add_spacer(height=20)
                        dpg.add_text("Select a sequence from the dropdown to preview...",
                                     color=theme.TEXT_NORMAL, indent=450, tag="seq_preview_text")

                    # KARTA: LOGGER
                    with dpg.tab(label="LOGGER"):
                        dpg.add_spacer(height=10)
                        with dpg.group(horizontal=True):
                            dpg.add_text("Ground Station Logs", indent=400)
                            dpg.add_spacer(width=300)
                            dpg.add_text("Log level:")
                            dpg.add_combo(items=["INFO", "DEBUG", "WARNING", "ERROR"], default_value="INFO", width=100)
                        with dpg.child_window(width=-1, height=-1, border=False, tag="terminal_container"):
                            dpg.add_text("", tag=self.terminal_id)

                    # KARTA: FLIGHT REPLAY
                    with dpg.tab(label="FLIGHT REPLAY"):
                        dpg.add_spacer(height=10)
                        dpg.add_text("POST-FLIGHT SIMULATION & LOG REPLAY", color=theme.ACCENT_PRIMARY)

                        # Kontrolki odtwarzacza (PLAY, PAUSE, STOP)
                        with dpg.group(horizontal=True):
                            play_btn = dpg.add_button(label="PLAY REPLAY", width=100, tag="replay_play_btn")
                            pause_btn = dpg.add_button(label="PAUSE", width=80, tag="replay_pause_btn")
                            stop_btn = dpg.add_button(label="STOP / RESET", width=100, tag="replay_stop_btn")

                            dpg.add_spacer(width=20)
                            dpg.add_slider_float(label="Playback Speed", default_value=1.0, min_value=0.5,
                                                 max_value=5.0, width=150, tag="replay_speed_slider")

                            # Bindowanie dedykowanego motywu dla przycisków odtwarzacza
                            replay_theme = theme.create_button_theme(theme.COLOR_TEAL)
                            for btn in [play_btn, pause_btn, stop_btn]:
                                dpg.bind_item_theme(btn, replay_theme)

                        dpg.add_spacer(height=20)
                        dpg.add_text("Wybierz plik z logami misji z dysku:", color=theme.TEXT_NORMAL)

                        # NOWE ELEMENTY: Przycisk wyboru i etykieta ścieżki pliku
                        with dpg.group(horizontal=True):
                            select_file_btn = dpg.add_button(label="CHOOSE LOG FILE", width=180,
                                                             tag="replay_select_file_btn")
                            dpg.bind_item_theme(select_file_btn, replay_theme)

                        dpg.add_spacer(height=10)
                        # Tu wyświetli się nazwa załadowanego pliku
                        dpg.add_text("No file selected.", tag="replay_file_path_text", color=theme.STATUS_AMBER)

                    # KARTA: GPS TRACKER
                    with dpg.tab(label="GPS TRACKER"):
                        dpg.add_spacer(height=10)
                        dpg.add_text("LIVE ROCKET TRAJECTORY (TOP-DOWN VIEW)", color=theme.ACCENT_PRIMARY)

                        # Wykres mapy (X=Długość, Y=Szerokość)
                        with dpg.plot(height=-1, width=-1, no_menus=False):
                            dpg.add_plot_legend()

                            # Oś X: Longitude (Długość geograficzna - Wschód/Zachód)
                            dpg.add_plot_axis(dpg.mvXAxis, label="Longitude (°E)", tag="gps_x_axis")

                            # Oś Y: Latitude (Szerokość geograficzna - Północ/Południe)
                            with dpg.plot_axis(dpg.mvYAxis, label="Latitude (°N)", tag="gps_y_axis"):
                                # Ślad trajektorii
                                dpg.add_line_series([], [], label="Flight Path", tag="gps_path_series")
                                # Aktualna pozycja (kropka)
                                dpg.add_scatter_series([], [], label="Current Position", tag="gps_current_series")

            dpg.add_separator()

            with dpg.file_dialog(directory_selector=False, show=False, tag="replay_file_dialog", width=700, height=450):
                dpg.add_file_extension(".csv", color=(0, 255, 0, 255), custom_text="[CSV Raw Telemetry Frames]")
                dpg.add_file_extension(".txt", color=(0, 255, 255, 255), custom_text="[TXT Console Log dumps]")
                dpg.add_file_extension(".*", color=(150, 150, 150, 255), custom_text="All files")

            # --- 3. PRZYKLEJONY PANEL DOLNY ---
            with dpg.group(tag="fixed_bottom_panel"):
                # Pasek komend (zmniejszone szerokości dla lepszego pasowania)
                with dpg.child_window(height=45, border=False, no_scrollbar=True):
                    with dpg.group(horizontal=True):
                        dpg.add_input_text(hint="Enter command to rocket...", width=-280, tag="cmd_input")
                        dpg.add_button(label="SEND", width=75, tag="send_btn")
                        dpg.add_button(label="CLEAR", width=75, tag="clear_btn")
                        dpg.add_checkbox(label="AUTO", default_value=True, tag="autoscroll_check")

                # Pasek Mission Critical
                with dpg.child_window(height=50, border=False, no_scrollbar=True):
                    action_theme = theme.create_button_theme(theme.COLOR_TEAL)

                    with dpg.group(horizontal=True):
                        # Główne kontrolki
                        arm_btn = dpg.add_button(label="ARM SYSTEM", width=110, tag="arm_btn")
                        disarm_btn = dpg.add_button(label="DISARM", width=80, tag="disarm_btn")
                        reset_btn = dpg.add_button(label="RESET", width=70, tag="reset_btn")

                        dpg.add_spacer(width=15)

                        # Testy systemowe (Zgodnie z procedurą CRC)
                        buzzer_test_btn = dpg.add_button(label="TEST BUZZER", width=100, tag="buzzer_test_btn")
                        servo_test_btn = dpg.add_button(label="TEST SERVOS", width=100, tag="servo_test_btn")

                        dpg.add_spacer(width=15)

                        # Awaryjne
                        deploy_btn = dpg.add_button(label="EMERGENCY DEPLOY", width=140, tag="deploy_btn")
                        abort_btn = dpg.add_button(label="ABORT", width=70, tag="abort_btn")

                        # Bindowanie motywów
                        for btn in [arm_btn, disarm_btn, reset_btn, buzzer_test_btn, servo_test_btn, deploy_btn,
                                    abort_btn]:
                            dpg.bind_item_theme(btn, action_theme)

            # --- 4. OKNA WYSKAKUJĄCE (POPUPS) ---
            with dpg.window(label="Mission Control Settings", tag="settings_window", show=False,
                            width=400, height=250, modal=True, no_collapse=True, no_move=True):
                dpg.add_text("COMMUNICATION", color=theme.ACCENT_PRIMARY)
                dpg.add_combo(label="Baudrate", items=["9600", "57600", "115200", "921600"],
                              default_value="115200", width=150, tag="stg_baudrate")
                dpg.add_spacer(height=15)
                dpg.add_text("LOGGING", color=theme.ACCENT_PRIMARY)
                dpg.add_text("Directory: ./logs", color=theme.TEXT_NORMAL)
                dpg.add_spacer(height=20)
                dpg.add_button(label="CLOSE", width=100,
                               callback=lambda: dpg.configure_item("settings_window", show=False))


    def update_led(self, tag, color):
        """Metoda uaktualniająca kolor kółka rysowanego w Drawlist."""
        dpg.configure_item(tag, fill=color)