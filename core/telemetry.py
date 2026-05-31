import struct
import math
import time
import logging
from typing import Optional
from core.data_types import TelemetryFrame, MissionState, ConnectionStatus, Vector3

class TelemetryParser:
    # RAMKA (50 bajtów):
    # <  - Little Endian
    # B  - 1x uint8 (preambuła)
    # I  - 1x uint32 (timestamp)
    # B, B - 2x uint8 (stan, ost. komenda)
    # h, h - 2x int16 (wysokość decymetry, temp 1/100 C)
    # 9h - 9x int16 (3x mag, 3x acc, 3x gyro)
    # B, B - 2x uint8 (GPS fix, liczba satelit)
    # 3f - 3x float (GPS lat, lon, alt)
    # B  - 1x uint8 (GPIO state)
    # H  - 1x uint16 (napięcie baterii 1/100 V)
    # B  - 1x uint8 (RSSI)
    # 3s - 3 bajty zakończenia (\n\r\0)

    FRAME_FORMAT = "< B I B B h h 9h B B 3f B H B 3s"
    FRAME_SIZE = 50

    def __init__(self):
        self.state = TelemetryFrame()
        self._last_valid_time = 0.0
        self.logger = logging.getLogger("MissionControl")
        self._prev_mission_state = MissionState.IDLE
        self._prev_conn_status = ConnectionStatus.DISCONNECTED
        self._last_drop_time = 0

    def parse_frame(self, frame_bytes: bytes) -> Optional[TelemetryFrame]:
        if len(frame_bytes) != self.FRAME_SIZE:
            return None

        try:
            unpacked = struct.unpack(self.FRAME_FORMAT, frame_bytes)

            self.state.timestamp_ms = unpacked[1]
            stan_raw = unpacked[2]
            self.state.last_command = unpacked[3]

            self.state.altitude = unpacked[4] / 10.0
            self.state.temp = unpacked[5] / 100.0 # 1/100 st.C

            self.state.mag = Vector3(unpacked[6], unpacked[7], unpacked[8])
            self.state.accel = Vector3(unpacked[9], unpacked[10], unpacked[11])
            self.state.gyro = Vector3(unpacked[12], unpacked[13], unpacked[14])

            # GPS
            self.state.gps_fix = unpacked[15]
            self.state.gps_sats = unpacked[16]
            self.state.gps_lat = unpacked[17]
            self.state.gps_lon = unpacked[18]
            self.state.gps_alt = unpacked[19]

            self.state.gpio_state = unpacked[20]
            self.state.voltage = unpacked[21] / 100.0
            self.state.rssi = unpacked[22]

            try:
                new_state = MissionState(stan_raw)
                if new_state != self._prev_mission_state:
                    self.logger.info(f"Zmiana stanu rakiety: {self._prev_mission_state.name} -> {new_state.name}")
                    self._prev_mission_state = new_state
                self.state.state = new_state
            except ValueError:
                pass

            acc = self.state.accel
            pitch_rad = math.atan2(-acc.x, math.sqrt(acc.y ** 2 + acc.z ** 2 + 1e-6))
            roll_rad = math.atan2(acc.y, acc.z + 1e-6)
            self.state.pitch = math.degrees(pitch_rad)
            self.state.roll = math.degrees(roll_rad)
            self.state.yaw = 0.0

            self._last_valid_time = time.time()
            self.state.last_update = self._last_valid_time

            return self.state

        except struct.error as e:
            self.logger.error(f"Błąd rozpakowania struktury: {e}")
            return None

    def get_connection_status(self) -> ConnectionStatus:
        now = time.time()
        time_since_last = now - self._last_valid_time
        time_since_drop = now - self._last_drop_time

        if time_since_last > 2.0:
            current_status = ConnectionStatus.DISCONNECTED
        elif self.state.voltage > 0 and self.state.voltage < 3.4:
            current_status = ConnectionStatus.ERROR
        elif time_since_drop < 1.0:
            current_status = ConnectionStatus.DROPPED_FRAMES
        else:
            current_status = ConnectionStatus.CONNECTED

        if current_status != self._prev_conn_status:
            if current_status == ConnectionStatus.DISCONNECTED:
                self.logger.error(f"UTRATA SYGNAŁU: Brak danych od {time_since_last:.1f}s")
            elif current_status == ConnectionStatus.ERROR:
                self.logger.critical(f"BŁĄD ZASILANIA: Napięcie spadło do {self.state.voltage:.2f}V!")
            elif current_status == ConnectionStatus.DROPPED_FRAMES:
                self.logger.warning(f"DEGRADACJA LINKU: Wykryto luki w transmisji LoRa")
            elif current_status == ConnectionStatus.CONNECTED:
                if self._prev_conn_status in [ConnectionStatus.DISCONNECTED, ConnectionStatus.ERROR]:
                    self.logger.info("POŁĄCZENIE ODZYSKANE: Link telemetrii stabilny")

            self._prev_conn_status = current_status

        return current_status