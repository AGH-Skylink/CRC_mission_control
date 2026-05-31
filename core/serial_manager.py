import serial
import serial.tools.list_ports
import threading
import queue
import time
import logging
import glob
import sys

from core.data_types import ConnectionStatus


class SerialManager:
    def __init__(self):
        self.ser = None
        self.is_running = False
        self.read_thread = None
        self.raw_queue = queue.Queue()
        self.status = ConnectionStatus.DISCONNECTED
        self.logger = logging.getLogger("MissionControl")

        self.bitrate = 0.0
        self._bytes_count = 0
        self._last_stat_time = time.time()

    def scan_ports(self):
        ports = []

        for port in serial.tools.list_ports.comports():
            desc = (port.description or "").lower()
            hwid = (port.hwid or "").lower()
            device = (port.device or "").lower()

            is_bluetooth = "bluetooth" in desc or "bluetooth" in hwid or "bth" in hwid or "bluetooth" in device

            if not is_bluetooth:
                ports.append(port.device)

        if sys.platform.startswith('darwin'):
            virtual_ptys = glob.glob('/dev/ttys[0-9][0-9][0-9]')
            for p in virtual_ptys:
                if p not in ports:
                    ports.append(p)

        self.logger.info(f"Scanned ports: {ports}")
        return ports

    def connect(self, port, baudrate=115200):
        self.logger.info(f"Attempting to connect to {port} at {baudrate} baud...")
        try:
            self.ser = serial.Serial(port, baudrate, timeout=0.1)
            self.is_running = True
            self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.read_thread.start()
            self.status = ConnectionStatus.CONNECTED
            self.logger.info(f"Successfully connected to {port}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to {port}: {e}")
            self.status = ConnectionStatus.ERROR
            return False

    def disconnect(self):
        if not self.is_running:
            return

        self.is_running = False
        if self.read_thread:
            self.read_thread.join(timeout=1.0)
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.logger.warning("Serial connection closed by user")
        self.status = ConnectionStatus.DISCONNECTED

    def _read_loop(self):
        sync_buffer = bytearray()

        while self.is_running:
            if self.ser and self.ser.is_open:
                try:
                    if self.ser.in_waiting > 0:
                        chunk = self.ser.read(self.ser.in_waiting)
                        self._bytes_count += len(chunk)
                        sync_buffer.extend(chunk)

                        while len(sync_buffer) >= 50:
                            if sync_buffer[47:50] == b'\n\r\0':
                                frame_bytes = sync_buffer[:50]
                                self.raw_queue.put(frame_bytes)
                                sync_buffer = sync_buffer[50:]
                            else:
                                sync_buffer.pop(0)

                    self._update_bitrate()
                except Exception as e:
                    self.logger.critical(f"Serial read error: {e}")
                    self.status = ConnectionStatus.ERROR
                    self.is_running = False
            time.sleep(0.001)

    def _update_bitrate(self):
        now = time.time()
        diff = now - self._last_stat_time
        if diff >= 1.0:
            self.bitrate = (self._bytes_count * 8) / (diff * 1024)  # kb/s
            self._bytes_count = 0
            self._last_stat_time = now

    def send_data(self, data):
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(f"{data}\n".encode())
                self.logger.debug(f"Raw data sent: {data}")
                return True
            except Exception as e:
                self.logger.error(f"Failed to send data '{data}': {e}")
                self.status = ConnectionStatus.ERROR
        return False