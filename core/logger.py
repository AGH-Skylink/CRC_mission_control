import logging
import csv
import time
from datetime import datetime
from pathlib import Path
from core.data_types import TelemetryFrame


class DPGHandler(logging.Handler):

    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def emit(self, record):
        log_entry = self.format(record)
        if self.callback:
            self.callback(log_entry, record.levelno)


class MissionLogger:
    def __init__(self, log_dir="logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.telemetry_file = self.log_dir / f"telemetry_{self.session_id}.csv"
        self.system_file = self.log_dir / f"system_{self.session_id}.log"
        self.raw_file = self.log_dir / f"raw_frames_{self.session_id}.csv"

        self._setup_system_logger()
        self._setup_csv_header()
        self._setup_raw_header()

    def _setup_system_logger(self):
        self.logger = logging.getLogger("MissionControl")
        self.logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            '[%(asctime)s.%(msecs)03d] [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        )

        file_handler = logging.FileHandler(self.system_file)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def _setup_csv_header(self):
        headers = [
            "timestamp", "state", "last_command",
            "acc_x", "acc_y", "acc_z",
            "gyr_x", "gyr_y", "gyr_z",
            "mag_x", "mag_y", "mag_z",
            "alt", "temp", "volt", "rssi",
            "pitch", "roll", "yaw",
            "gps_fix", "gps_sats", "gps_lat", "gps_lon", "gps_alt"
        ]
        with open(self.telemetry_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)

    def log_telemetry(self, frame: TelemetryFrame):
        try:
            with open(self.telemetry_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    time.time(),
                    frame.state.value,
                    frame.last_command,
                    frame.accel.x, frame.accel.y, frame.accel.z,
                    frame.gyro.x, frame.gyro.y, frame.gyro.z,
                    frame.mag.x, frame.mag.y, frame.mag.z,
                    frame.altitude,
                    frame.temp,
                    frame.voltage,
                    frame.rssi,
                    frame.pitch,
                    frame.roll,
                    frame.yaw,
                    frame.gps_fix,
                    frame.gps_sats,
                    frame.gps_lat,
                    frame.gps_lon,
                    frame.gps_alt
                ])
        except Exception as e:
            self.error(f"Krytyczny błąd zapisu telemetrii: {e}")


    def info(self, msg): self.logger.info(msg)
    def debug(self, msg): self.logger.debug(msg)
    def warning(self, msg): self.logger.warning(msg)
    def error(self, msg): self.logger.error(msg)
    def critical(self, msg): self.logger.critical(msg)

    def add_ui_handler(self, callback):
        handler = DPGHandler(callback)
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', '%H:%M:%S')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log_raw_frame(self, raw_line: str):
        try:
            with open(self.raw_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([time.time(), raw_line])
                f.flush()
        except Exception as e:
            self.error(f"Błąd zapisu surowej ramki: {e}")

    def _setup_raw_header(self):
        with open(self.raw_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "raw_data"])