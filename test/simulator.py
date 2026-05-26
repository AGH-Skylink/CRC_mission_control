import serial
import time
import math
import random
import struct


class RocketSimulator:
    def __init__(self, port='/tmp/virtualCOM1', baudrate=115200):
        try:
            self.ser = serial.Serial(port, baudrate, timeout=1)
            print(f"🚀 Simulator started on {port}")
        except Exception as e:
            print(f"❌ Error: Could not open port {port}. {e}")
            exit()

        self.start_time = time.time()

        # Stan fizyczny rakiety
        self.state = 0  # 0: IDLE, 1: LAUNCH, 2: ASCENT, 3: APOGEE, 4: DESCENT, 5: LANDING
        self.altitude = 0.0
        self.velocity = 0.0
        self.pitch = 0.0
        self.roll = 0.0
        self.yaw = 0.0
        self.voltage = 4.2  # Start od w pełni naładowanej baterii 18650
        self.temp = 20.0

        # C Struct unpacking format dla 58 bajtów (Little Endian):
        self.FRAME_FORMAT = "< B I B B h h h h h h h h h h h 20s B H b H 3s"

    def update_physics(self):
        """Generuje fizykę misji zgodną z raportem CRC 2026."""
        elapsed = time.time() - self.start_time

        # Prosta maszyna stanów zmapowana na IntEnum
        if self.state == 0 and elapsed > 5:
            self.state = 1
        elif self.state == 1 and elapsed > 6:
            self.state = 2
        elif self.state == 2 and self.velocity < 0:
            self.state = 3
        elif self.state == 3:
            self.state = 4
        elif self.state == 4 and self.altitude <= 0:
            self.state = 5
            self.altitude = 0.0

        # Modelowanie lotu
        if self.state == 1:
            self.velocity += 8.8  # G-force
            self.altitude += self.velocity * 0.1
        elif self.state == 2:
            self.velocity -= 0.98  # Grawitacja
            self.altitude += self.velocity * 0.1
            self.pitch = 85.0 + random.uniform(-2, 2)
            self.roll += 5.0  # Obrót stabilizacyjny
        elif self.state == 4:
            self.velocity = -8.0  # Docelowa prędkość opadania
            self.altitude += self.velocity * 0.1
            self.pitch = random.uniform(-10, 10)
            self.roll += 2.0

        # Zabezpieczenie przed wysokością ujemną
        if self.altitude < 0:
            self.altitude = 0.0

        # Degradacja baterii i szum temp
        self.voltage -= 0.0001
        self.temp += random.uniform(-0.1, 0.1)

    def generate_frame(self):
        self.update_physics()
        elapsed_ms = int((time.time() - self.start_time) * 1000)

        # Magia dla Navballa: Obliczamy co zarejestrowałby akcelerometr
        # Zakładamy 1G = 1000 jednostek LSB (Typowo dla MPU9250 to np. 16384 lub 8192)
        p_rad = math.radians(self.pitch)
        r_rad = math.radians(self.roll)

        acc_x = int(-math.sin(p_rad) * 1000)
        acc_y = int(math.sin(r_rad) * math.cos(p_rad) * 1000)
        acc_z = int(math.cos(r_rad) * math.cos(p_rad) * 1000)

        # Formatowanie TBD dla GPS (wymaga dokładnie 20 bajtów)
        gps_bytes = b"NO_FIX_SIMULATED".ljust(20, b'\0')

        # Pakowanie wszystkiego w binarną ramkę 58 bajtów
        frame = struct.pack(
            self.FRAME_FORMAT,
            0xAA,  # B: preambuła
            elapsed_ms,  # I: timestamp
            self.state,  # B: stan
            0,  # B: ostatnia komenda
            int(self.altitude * 10),  # h: wysokość [dm]
            int(self.temp),  # h: temperatura [°C]
            0, 0, 0,  # 3xh: mag x,y,z
            acc_x, acc_y, acc_z,  # 3xh: acc x,y,z (dla Navballa)
            0, 0, 0,  # 3xh: gyro x,y,z
            gps_bytes,  # 20s: GPS
            0,  # B: GPIO
            int(self.voltage * 1000),  # H: Napięcie w mV
            random.randint(-85, -60),  # b: RSSI z szumem
            0x0000,  # H: CRC (fake)
            b'\n\r\0'  # 3s: zakończenie
        )
        return frame

    def run(self):
        """Wysyła dane z częstotliwością 20Hz (co 50ms)."""
        frame_count = 0
        while True:
            try:
                frame_count += 1
                frame_bytes = self.generate_frame()

                # Zamiast f"{line}\n".encode(), wysyłamy od razu spakowane bajty
                self.ser.write(frame_bytes)

                # Symulacja zerwanego pakietu co ~50 ramek
                if frame_count % 50 == 0:
                    time.sleep(0.1)  # Opóźnienie wywoła żółty status, jeśli obsłużysz to w telemetrii

                time.sleep(0.05)
            except KeyboardInterrupt:
                self.ser.close()
                print("\n🛑 Simulator stopped.")
                break


if __name__ == "__main__":
    # Pamiętaj o ustawieniu prawidłowego portu na swoim Macu (np. /dev/ttys005)
    sim = RocketSimulator(port='/dev/ttys003')
    sim.run()