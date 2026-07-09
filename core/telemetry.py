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

        if frame_bytes[0] != self.PREAMBLE:
            # Ramka nie zaczyna sie od '$' - resynchronizacja w SerialManager
            # powinna temu zapobiegac, ale sprawdzamy defensywnie.
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

            self.state.altitude = altitude_raw / 10.0   # decymetry -> metry
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

            # UWAGA: aktualny firmware GS (CRC-LoRa) wysyla tu SUROWA wartosc
            # ADC, nie napiecie w V (w kodzie GS jest komentarz
            # "dodac funkcje przeliczajaca" - konwersja jeszcze nie istnieje).
            # Dzielimy przez 100.0 zgodnie z udokumentowanym formatem ramki
            # (1/100 V), zeby MC bylo gotowe, gdy GS zacznie wysylac juz
            # przeliczona wartosc. Do tego czasu ta liczba NIE jest realnym
            # napieciem w woltach.
            self.state.voltage = voltage_raw / 100.0

            # RSSI: firmware liczy LoRa_getRSSI() = -164 + read (wartosc
            # ujemna, int), ale zapisuje ja do bajtu przez (uint8_t)cast -
            # co obcina znak. Odzyskujemy to jako 8-bitowa liczba ze znakiem
            # (U2). Dla bardzo slabego sygnalu (< -128 dBm) wartosc i tak
            # bedzie niejednoznaczna z powodu tego bledu w firmware - to nie
            # da sie naprawic wylacznie po stronie odbiorcy.
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
