import bisect
import csv
import logging
import struct
from typing import Optional

from core.telemetry import TelemetryParser


class CsvSensorFeed:
    """
    Podmienia pola "sensorowe" w JUZ ODEBRANEJ, surowej 50-bajtowej ramce
    telemetrycznej wartosciami wczytanymi z pliku CSV, PRZED przekazaniem
    ramki do TelemetryParser.parse_frame().

    Uzycie w main.py, w petli run():

        raw_bytes = self.serial.raw_queue.get()
        raw_bytes = self.csv_feed.overlay(raw_bytes)   # <-- nowa linijka
        frame = self.parser.parse_frame(raw_bytes)

    Reszta aplikacji (parser, logger, UI) nie wie, ze cos zostalo podmienione -
    dostaje normalna, poprawna pod wzgledem formatu ramke 50-bajtowa.

    Oczekiwany format CSV (naglowek wymagany, kolejnosc kolumn dowolna):

        t_ms,altitude_m,temp_c,mag_x,mag_y,mag_z,accel_x,accel_y,accel_z,
        gyro_x,gyro_y,gyro_z,gps_lat,gps_lon,gps_alt,voltage

    Jednostki - zgodne z tym co realnie leci w ramce (patrz core/telemetry.py):
        t_ms        - czas misji w ms, MUSI byc rosnaco posortowany
        altitude_m  - metry (relatywne lub bezwzgledne - Twoj wybor, i tak
                      TelemetryParser sam odejmuje baseline z 1. ramki)
        temp_c      - stopnie Celsjusza
        mag/accel/gyro_* - SUROWE liczby calkowite int16 (takie jak wysylane
                      z firmware, bez skalowania - tak samo jak w simulator.py)
        gps_lat/lon - stopnie dziesietne (float)
        gps_alt     - metry (float)
        voltage     - wolty (V), np. 4.05

    Wiersze sa dopasowywane do kazdej odebranej ramki po t_ms metoda
    "najblizszego sasiada" (nearest neighbour), wiec czestotliwosc ramek
    z serial NIE musi pokrywac sie z czestotliwoscia probek w CSV.
    """

    def __init__(self, csv_path: Optional[str] = None):
        self.logger = logging.getLogger("MissionControl")
        self.enabled = False
        self._timestamps = []   # posortowana lista t_ms (int)
        self._rows = []         # rownolegla lista dict-ow z wartosciami

        if csv_path:
            self.load(csv_path)

    def load(self, csv_path: str) -> bool:
        self._timestamps = []
        self._rows = []

        required_cols = {
            "t_ms", "altitude_m", "temp_c",
            "mag_x", "mag_y", "mag_z",
            "accel_x", "accel_y", "accel_z",
            "gyro_x", "gyro_y", "gyro_z",
            "gps_lat", "gps_lon", "gps_alt",
            "voltage",
        }

        try:
            with open(csv_path, "r", newline="") as f:
                reader = csv.DictReader(f)

                missing = required_cols - set(reader.fieldnames or [])
                if missing:
                    self.logger.error(
                        f"CSV {csv_path}: brakuje kolumn: {sorted(missing)}"
                    )
                    self.enabled = False
                    return False

                for row in reader:
                    t_ms = int(float(row["t_ms"]))
                    self._timestamps.append(t_ms)
                    self._rows.append({
                        "altitude_m": float(row["altitude_m"]),
                        "temp_c": float(row["temp_c"]),
                        "mag": (int(float(row["mag_x"])), int(float(row["mag_y"])), int(float(row["mag_z"]))),
                        "accel": (int(float(row["accel_x"])), int(float(row["accel_y"])), int(float(row["accel_z"]))),
                        "gyro": (int(float(row["gyro_x"])), int(float(row["gyro_y"])), int(float(row["gyro_z"]))),
                        "gps_lat": float(row["gps_lat"]),
                        "gps_lon": float(row["gps_lon"]),
                        "gps_alt": float(row["gps_alt"]),
                        "voltage": float(row["voltage"]),
                    })

            if not self._timestamps:
                self.logger.error(f"CSV {csv_path}: plik jest pusty")
                self.enabled = False
                return False

            if any(a > b for a, b in zip(self._timestamps, self._timestamps[1:])):
                self.logger.error(f"CSV {csv_path}: kolumna t_ms nie jest posortowana rosnaco")
                self.enabled = False
                return False

            self.enabled = True
            self.logger.info(f"Wczytano {len(self._timestamps)} probek sensorow z {csv_path}")
            return True

        except Exception as e:
            self.logger.error(f"Nie udalo sie wczytac CSV {csv_path}: {e}")
            self.enabled = False
            return False

    def _row_for_timestamp(self, t_ms: int) -> dict:
        idx = bisect.bisect_left(self._timestamps, t_ms)

        if idx == 0:
            return self._rows[0]
        if idx == len(self._timestamps):
            return self._rows[-1]

        before_t = self._timestamps[idx - 1]
        after_t = self._timestamps[idx]

        if (t_ms - before_t) <= (after_t - t_ms):
            return self._rows[idx - 1]
        return self._rows[idx]

    @staticmethod
    def _clip_i16(v: float) -> int:
        return max(-32768, min(32767, int(round(v))))

    @staticmethod
    def _clip_u16(v: float) -> int:
        return max(0, min(65535, int(round(v))))

    def overlay(self, raw_bytes: bytes) -> bytes:
        """
        Jesli feed nie jest wlaczony (brak/zly CSV) - zwraca ramke bez zmian,
        wiec dopoki CSV nie jest gotowy, cala reszta aplikacji dziala
        dokladnie tak jak dzisiaj (na danych z prawdziwej awioniki / symulatora).
        """
        if not self.enabled:
            return raw_bytes

        if len(raw_bytes) != TelemetryParser.FRAME_SIZE:
            return raw_bytes

        if raw_bytes[0] != TelemetryParser.PREAMBLE:
            return raw_bytes

        try:
            (
                preamble,
                timestamp,
                stan_raw,
                last_command,
                _altitude_raw,
                _temp_raw,
                _mx, _my, _mz,
                _ax, _ay, _az,
                _gx, _gy, _gz,
                gps_fix,
                gps_sats,
            ) = struct.unpack(TelemetryParser.FRAME_FORMAT_PART1, raw_bytes[0:31])

            gpio_state, _voltage_raw, rssi_raw, end = struct.unpack(
                TelemetryParser.FRAME_FORMAT_PART3, raw_bytes[43:50]
            )

            row = self._row_for_timestamp(timestamp)

            altitude_raw = self._clip_i16(row["altitude_m"] * 10.0)
            temp_raw = self._clip_i16(row["temp_c"] * 100.0)
            mx, my, mz = (self._clip_i16(v) for v in row["mag"])
            ax, ay, az = (self._clip_i16(v) for v in row["accel"])
            gx, gy, gz = (self._clip_i16(v) for v in row["gyro"])
            voltage_raw = self._clip_u16(row["voltage"] * 100.0)

            part1 = struct.pack(
                TelemetryParser.FRAME_FORMAT_PART1,
                preamble, timestamp, stan_raw, last_command,
                altitude_raw, temp_raw,
                mx, my, mz,
                ax, ay, az,
                gx, gy, gz,
                gps_fix, gps_sats,
            )

            part2 = struct.pack(
                TelemetryParser.FRAME_FORMAT_PART2,
                row["gps_lat"], row["gps_lon"], row["gps_alt"],
            )

            part3 = struct.pack(
                TelemetryParser.FRAME_FORMAT_PART3,
                gpio_state, voltage_raw, rssi_raw, end,
            )

            return part1 + part2 + part3

        except struct.error as e:
            self.logger.error(f"CsvSensorFeed: blad pakowania ramki: {e}")
            return raw_bytes
