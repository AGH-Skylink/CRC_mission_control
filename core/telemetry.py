import struct
import math
import time
import logging
from typing import Optional
from core.data_types import TelemetryFrame, MissionState, ConnectionStatus, Vector3

class TelemetryParser:
    # C Struct unpacking format dla 58 bajtów:
    # <  - Little Endian (standard dla STM32)
    # B  - 1x uint8 (preambula)
    # I  - 1x uint32 (timestamp)
    # B, B - 2x uint8 (stan, ost. komenda)
    # h, h - 2x int16 (wysokość dm, temperatura)
    # 9h - 9x int16 (3x mag, 3x acc, 3x gyro)
    # 20s - 20 bajtów char (GPS - obecnie śmieci)
    # B  - 1x uint8 (GPIO)
    # H  - 1x uint16 (napięcie)
    # b  - 1x int8 (RSSI)
    # H  - 1x uint16 (CRC)
    # 3s - 3 bajty zakonczenia
    FRAME_FORMAT = "< B I B B h h h h h h h h h h h 20s B H b H 3s"
    FRAME_SIZE = 58

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
            self.state.temp = unpacked[5]

            self.state.mag = Vector3(unpacked[6], unpacked[7], unpacked[8])
            self.state.accel = Vector3(unpacked[9], unpacked[10], unpacked[11])
            self.state.gyro = Vector3(unpacked[12], unpacked[13], unpacked[14])

            self.state.gpio_state = unpacked[16]
            self.state.voltage = unpacked[17] / 1000.0
            self.state.rssi = unpacked[18]

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
            current_status = ConnectionStatus.DISCONNECTED  # BLACK

        elif self.state.voltage > 0 and self.state.voltage < 3.4:
            current_status = ConnectionStatus.ERROR  # RED

        elif time_since_drop < 1.0:
            current_status = ConnectionStatus.DROPPED_FRAMES  # YELLOW

        else:
            current_status = ConnectionStatus.CONNECTED  # GREEN

        if current_status != self._prev_conn_status:
            if current_status == ConnectionStatus.DISCONNECTED:
                self.logger.error(f"UTRATA SYGNAŁU: Brak danych od {time_since_last:.1f}s")

            elif current_status == ConnectionStatus.ERROR:
                self.logger.critical(f"BŁĄD ZASILANIA: Napięcie spadło do {self.state.voltage:.2f}V!")

            elif current_status == ConnectionStatus.DROPPED_FRAMES:
                self.logger.warning(
                    f"DEGRADACJA LINKU: Wykryto luki w transmisji LoRa (Suma zgubionych: {self.state.dropped_frames})")

            elif current_status == ConnectionStatus.CONNECTED:
                if self._prev_conn_status in [ConnectionStatus.DISCONNECTED, ConnectionStatus.ERROR]:
                    self.logger.info("POŁĄCZENIE ODZYSKANE: Link telemetrii stabilny")

            self._prev_conn_status = current_status

        return current_status