import struct
import math
import time
import logging
from typing import Optional
from core.data_types import TelemetryFrame, MissionState, ConnectionStatus, Vector3

class TelemetryParser:
    # RAMKA (50 bajtow) - zweryfikowana wprost w kodzie ground station
    # (AGH-Skylink/CRC-LoRa, branch Pirx, OldAvio/Core/Src/FlightComputer.c).
    #
    # UWAGA: to NIE jest jednolita ramka little- ani big-endian. Firmware
    # pakuje wiekszosc pol RECZNIE (>>24/>>16/>>8/&0xFF), co daje BIG-ENDIAN,
    # a pola GPS (lat/lon/alt) kopiuje surowym memcpy z natywnej (little-endian)
    # reprezentacji floata na STM32/ARM. Parsowanie calej ramki jednym
    # struct.unpack("<...") (jak bylo wczesniej) jest bledne dla wszystkiego
    # oprocz GPS - stad ramka byla odczytywana zle.
    #
    #   0      preambula '$'                          uint8
    #   1-4    timestamp                       BIG-ENDIAN  uint32
    #   5      stan                                    uint8
    #   6      ostatnia komenda                        uint8
    #   7-8    wysokosc [decymetry]            BIG-ENDIAN  int16
    #   9-10   temperatura [1/100 C]           BIG-ENDIAN  int16
    #   11-16  magnetometr x,y,z               BIG-ENDIAN  3x int16
    #   17-22  akcelerometr x,y,z              BIG-ENDIAN  3x int16
    #   23-28  zyroskop x,y,z                  BIG-ENDIAN  3x int16
    #   29     GPS fix quality                         uint8 (firmware wysyla 0xFF gdy fix==1)
    #   30     GPS liczba satelitow                    uint8
    #   31-34  GPS lat                       LITTLE-ENDIAN  float32
    #   35-38  GPS lon                       LITTLE-ENDIAN  float32
    #   39-42  GPS alt                       LITTLE-ENDIAN  float32
    #   43     GPIO state (bitfield, patrz data_types.py)  uint8
    #   44-45  "napiecie baterii"               BIG-ENDIAN  uint16
    #   46     RSSI                                    uint8
    #   47-49  zakonczenie \n \r \0                    3x uint8

    FRAME_FORMAT_PART1 = ">BIBBhh3h3h3hBB"  # bajty 0-30 (31 bajtow), big-endian
    FRAME_FORMAT_PART2 = "<3f"              # bajty 31-42 (12 bajtow), GPS floats, little-endian
    FRAME_FORMAT_PART3 = ">BHB3s"           # bajty 43-49 (7 bajtow), big-endian

    FRAME_SIZE = 50
    PREAMBLE = 0x24  # '$'
    ACCEL_NOSE_SIGN = -1.0

    def __init__(self):
        self.state = TelemetryFrame()
        self._last_valid_time = 0.0
        self.logger = logging.getLogger("MissionControl")
        self._prev_mission_state = MissionState.IDLE
        self._prev_conn_status = ConnectionStatus.DISCONNECTED
        self._last_drop_time = 0
        self._altitude_baseline_raw = None  # ustawiane na 1. odebranej ramce
        self._orientation_baseline = None   # (pitch_bias_deg, roll_bias_deg), ustawiane na 1. ramce

    def reset_altitude_baseline(self):
        self._altitude_baseline_raw = None

    def reset_orientation_baseline(self):
        self._orientation_baseline = None

    def parse_frame(self, frame_bytes: bytes) -> Optional[TelemetryFrame]:
        if len(frame_bytes) != self.FRAME_SIZE:
            return None

        if frame_bytes[0] != self.PREAMBLE:
            self.logger.warning(
                f"Odrzucono ramke: zla preambula 0x{frame_bytes[0]:02X} (oczekiwano 0x24)"
            )
            return None

        try:
            (
                preamble,
                timestamp,
                stan_raw,
                last_command,
                altitude_raw,
                temp_raw,
                mx, my, mz,
                ax, ay, az,
                gx, gy, gz,
                gps_fix,
                gps_sats,
            ) = struct.unpack(self.FRAME_FORMAT_PART1, frame_bytes[0:31])

            gps_lat, gps_lon, gps_alt = struct.unpack(self.FRAME_FORMAT_PART2, frame_bytes[31:43])

            gpio_state, voltage_raw, rssi_raw, _end = struct.unpack(
                self.FRAME_FORMAT_PART3, frame_bytes[43:50]
            )

            self.state.timestamp_ms = timestamp
            self.state.last_command = last_command

            altitude_relative_m = altitude_raw / 10.0   # decymetry -> metry (wzgledem kalibracji GS)

            if self._altitude_baseline_raw is None:
                self._altitude_baseline_raw = altitude_relative_m

            self.state.altitude = altitude_relative_m - self._altitude_baseline_raw
            self.state.altitude_agl = self.state.altitude

            self.state.temp = temp_raw / 100.0          # 1/100 st.C -> st.C

            self.state.mag = Vector3(mx, my, mz)
            self.state.accel = Vector3(ax, ay, az)
            self.state.gyro = Vector3(gx, gy, gz)

            # GPS
            self.state.gps_fix = gps_fix
            self.state.gps_sats = gps_sats
            self.state.gps_lat = gps_lat
            self.state.gps_lon = gps_lon
            self.state.gps_alt = gps_alt

            self.state.gpio_state = gpio_state

            self.state.voltage = voltage_raw / 100.0

            self.state.rssi = rssi_raw - 256 if rssi_raw >= 128 else rssi_raw

            try:
                new_state = MissionState(stan_raw)
                if new_state != self._prev_mission_state:
                    self.logger.info(f"Zmiana stanu rakiety: {self._prev_mission_state.name} -> {new_state.name}")
                    self._prev_mission_state = new_state
                self.state.state = new_state
            except ValueError:
                pass

            acc = self.state.accel
            nose_accel = self.ACCEL_NOSE_SIGN * acc.x
            raw_pitch_deg = math.degrees(math.atan2(nose_accel, math.sqrt(acc.y ** 2 + acc.z ** 2 + 1e-6)))

            ROLL_NO_CONFIDENCE_RAW = 45.0   # ponizej tego roll = szum -> dazy do 0
            ROLL_FULL_CONFIDENCE_RAW = 90.0  # powyzej tego ufamy odczytowi w 100%
            ROLL_SMOOTHING = 0.25            # 0..1, wyzej = szybciej reaguje, nizej = gladsze

            horizontal_mag = math.sqrt(acc.y ** 2 + acc.z ** 2)
            raw_roll_deg = math.degrees(math.atan2(acc.y, acc.z + 1e-6))

            if self._orientation_baseline is None:
                pitch_bias = 90.0 - raw_pitch_deg
                roll_bias = 0.0 - raw_roll_deg
                self._orientation_baseline = (pitch_bias, roll_bias)

            pitch_bias, roll_bias = self._orientation_baseline

            calibrated_pitch = max(-90.0, min(90.0, raw_pitch_deg + pitch_bias))
            self.state.pitch = calibrated_pitch

            calibrated_roll_raw = raw_roll_deg + roll_bias

            if horizontal_mag <= ROLL_NO_CONFIDENCE_RAW:
                confidence = 0.0
            elif horizontal_mag >= ROLL_FULL_CONFIDENCE_RAW:
                confidence = 1.0
            else:
                confidence = (horizontal_mag - ROLL_NO_CONFIDENCE_RAW) / (
                    ROLL_FULL_CONFIDENCE_RAW - ROLL_NO_CONFIDENCE_RAW
                )

            target_roll_deg = confidence * calibrated_roll_raw  # dazy do 0 przy niskiej pewnosci
            self.state.roll += ROLL_SMOOTHING * (target_roll_deg - self.state.roll)

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
