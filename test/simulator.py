import serial
import time
import math
import random
import struct


class RocketSimulator:
    def __init__(self, port='/dev/ttys003', baudrate=115200):
        try:
            self.ser = serial.Serial(port, baudrate, timeout=1)
            print(f"Simulator started on {port}")
        except Exception as e:
            print(f"Error: Could not open port {port}. {e}")
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

        # NOWA RAMKA (50 bajtów):
        self.FRAME_FORMAT = "< B I B B h h 9h B B 3f B H B 3s"

    def update_physics(self):
        """Generuje fizykę misji."""
        elapsed = time.time() - self.start_time

        # Prosta maszyna stanów
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
            self.velocity += 8.8
            self.altitude += self.velocity * 0.1
        elif self.state == 2:
            self.velocity -= 0.98
            self.altitude += self.velocity * 0.1
            self.pitch = 85.0 + random.uniform(-2, 2)
            self.roll += 5.0
        elif self.state == 4:
            self.velocity = -8.0
            self.altitude += self.velocity * 0.1
            self.pitch = random.uniform(-10, 10)
            self.roll += 2.0

        if self.altitude < 0:
            self.altitude = 0.0

        # Degradacja baterii i szum temp
        self.voltage -= 0.0001
        self.temp += random.uniform(-0.1, 0.1)

    def generate_frame(self):
        self.update_physics()
        elapsed_ms = int((time.time() - self.start_time) * 1000)

        # Navball na bazie akcelerometru
        p_rad = math.radians(self.pitch)
        r_rad = math.radians(self.roll)

        acc_x = int(-math.sin(p_rad) * 1000)
        acc_y = int(math.sin(r_rad) * math.cos(p_rad) * 1000)
        acc_z = int(math.cos(r_rad) * math.cos(p_rad) * 1000)

        # Symulacja ruchu GPS (znoszenie przez wiatr po starcie)
        base_lat = 50.0647
        base_lon = 19.9231

        if self.state > 0:
            # Po starcie rakieta dryfuje w czasie
            drift = (elapsed_ms / 1000.0) * 0.00005
        else:
            drift = 0.0

        sim_lat = base_lat + (drift * 0.5)  # Lekki dryf na północ
        sim_lon = base_lon + drift  # Mocny dryf na wschód

        # Pakowanie wszystkiego w binarną ramkę 50 bajtów
        frame = struct.pack(
            self.FRAME_FORMAT,
            ord('$'),  # B: preambuła
            elapsed_ms,  # I: timestamp
            self.state,  # B: stan
            0,  # B: ostatnia komenda
            int(self.altitude * 10),  # h: wysokość [dm]
            int(self.temp * 100),  # h: temperatura [1/100 °C]
            0, 0, 0,  # 3xh: mag x,y,z
            acc_x, acc_y, acc_z,  # 3xh: acc x,y,z
            0, 0, 0,  # 3xh: gyro x,y,z
            1,  # B: GPS fix (symulowany fix)
            8,  # B: liczba satelitów
            sim_lat,  # f: GPS Lat (zmienna po wietrze)
            sim_lon,  # f: GPS Lon (zmienna po wietrze)
            self.altitude,  # f: GPS Alt
            0b00000000,  # B: GPIO State (zgodnie z rozpiską)
            int(self.voltage * 100),  # H: Napięcie [1/100 V]
            abs(random.randint(-85, -60)),  # B: RSSI (uint8)
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

                self.ser.write(frame_bytes)

                # Symulacja zerwanego pakietu co ~50 ramek
                if frame_count % 50 == 0:
                    time.sleep(0.1)

                time.sleep(0.05)
            except KeyboardInterrupt:
                self.ser.close()
                print("\n🛑 Simulator stopped.")
                break


if __name__ == "__main__":
    sim = RocketSimulator(port='/dev/ttys004')
    sim.run()