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

        # --- Profil lotu wg raportu koncowego "CRC 2026 Final Report" ---
        # (Parameter table + wykres OpenRocket "Vertical motion vs. time"):
        #   Expected apogee:        533 m
        #   Flight duration:        91.8 s
        #   Descent speed:          5.9 m/s
        #   Maximum acceleration:   104 m/s^2  (~10.6 g, krotki impuls silnika)
        #   Czas wznoszenia do apogeum wg logiki detekcji apogeum: ~11.5 s
        #     (bezpiecznik 11 s + margines na faze APOGEE)
        #
        # Model jest zbudowany na sztywnym rozkladzie czasowym (nie na
        # iteracyjnym calkowaniu predkosci jak poprzednio), zeby DOKLADNIE
        # trafiac w apogeum i calkowity czas lotu z raportu, niezaleznie od
        # dt miedzy klatkami - poprzednia wersja "dryfowala" i przy typowym
        # tempie wysylania ramek rakieta faktycznie leciala wyzej/dluzej niz
        # w rzeczywistym locie.
        self.T_WAIT = 5.0           # [s] czas w stanie IDLE przed startem
        self.T_BURN = 2.2           # [s] czas pracy silnika (stan LAUNCH)
        self.T_ASCENT = 11.5        # [s] czas od startu do apogeum (LAUNCH+ASCENT)
        self.APOGEE_ALT = 533.0     # [m] docelowe apogeum
        self.MAX_ACCEL_MS2 = 104.0  # [m/s^2] szczytowe przyspieszenie przy starcie
        self.DESCENT_SPEED = 5.9    # [m/s] predkosc opadania na spadochronie

        flight_duration = 91.8      # [s] laczny czas lotu (start -> ladowanie)
        self.T_DESCENT = max(flight_duration - self.T_ASCENT, 1.0)
        # Uwaga: apogee/T_DESCENT wychodzi ~6.6 m/s (nie dokladnie 5.9 m/s z
        # raportu) - te dwie liczby w raporcie nie sa idealnie spojne
        # (apogee/descent_speed dalyby dluzszy czas opadania niz
        # flight_duration-T_ASCENT). Priorytetyzujemy dokladny apogee i
        # dokladny CALKOWITY czas lotu (oba jawnie podane w tabeli
        # parametrow), a self.DESCENT_SPEED zostawiamy jako wartosc
        # informacyjna/etykietowa zblizona do raportu.

        # Sekwencja stanow z dokladnymi momentami przejsc (w sekundach od
        # startu silnika, tj. od konca T_WAIT):
        self._t_launch_end = self.T_BURN                    # koniec LAUNCH -> ASCENT
        self._t_apogee = self.T_ASCENT                       # koniec ASCENT -> APOGEE
        self._t_apogee_end = self.T_ASCENT + 0.3              # koniec APOGEE -> DESCENT
        self._t_landing = self.T_ASCENT + self.T_DESCENT      # koniec DESCENT -> LANDING

        # RAMKA (50 bajtow) - mieszany byte order, zgodny z rzeczywistym
        # firmware ground station (AGH-Skylink/CRC-LoRa, branch Pirx):
        # wiekszosc pol big-endian, GPS lat/lon/alt little-endian (natywny
        # float STM32). Patrz core/telemetry.py po pelny opis.
        self.FRAME_FORMAT_PART1 = ">BIBBhh3h3h3hBB"  # bajty 0-30
        self.FRAME_FORMAT_PART2 = "<3f"              # bajty 31-42 (GPS)
        self.FRAME_FORMAT_PART3 = ">BHB3s"           # bajty 43-49

    def update_physics(self):
        """Generuje fizyke misji na podstawie STALEGO rozkladu czasowego
        (nie iteracyjnej integracji), zeby dokladnie trafiac w apogeum i
        czas lotu z raportu koncowego, niezaleznie od tego jak czesto/
        rzadko wywolywana jest ta metoda (dt miedzy klatkami moze sie
        wahac, np. gdy petla wysylajaca ramki przycina sie)."""
        elapsed_total = time.time() - self.start_time
        t = elapsed_total - self.T_WAIT  # czas liczony od zaplonu silnika

        if t < 0:
            # WAITING
            self.state = 0
            self.altitude = 0.0
            self.velocity = 0.0
            self.pitch = 0.0
            self.roll = 0.0
            self.last_accel_g = 1.0  # rakieta lezy/stoi - 1g wzdluz osi

        elif t < self._t_launch_end:
            # POWERED ASCENT (praca silnika) - profil sin() od 0 do apogeum
            # daje gladki, monotoniczny wzrost wysokosci i dokladnie trafia
            # w docelowe apogeum/czas przy t = T_ASCENT (patrz galaz nizej).
            self.state = 1
            u = t / self.T_ASCENT
            self.altitude = self.APOGEE_ALT * math.sin(math.pi / 2 * u)
            self.velocity = (self.APOGEE_ALT * math.pi / (2 * self.T_ASCENT)) * math.cos(math.pi / 2 * u)
            self.pitch = 85.0 + random.uniform(-1, 1)
            self.roll += 2.0
            # Szczytowe przyspieszenie z raportu (104 m/s^2), maleje w
            # trakcie pracy silnika do ~0 na koncu fazy LAUNCH.
            burn_progress = t / self.T_BURN
            self.last_accel_g = (self.MAX_ACCEL_MS2 / 9.80665) * max(0.0, 1.0 - 0.5 * burn_progress)

        elif t < self._t_apogee:
            # UNPOWERED ASCENT (coasting) - ten sam gladki profil sin(),
            # bez skoku predkosci/wysokosci na granicy faz.
            self.state = 2
            u = t / self.T_ASCENT
            self.altitude = self.APOGEE_ALT * math.sin(math.pi / 2 * u)
            self.velocity = (self.APOGEE_ALT * math.pi / (2 * self.T_ASCENT)) * math.cos(math.pi / 2 * u)
            self.pitch = 85.0 + random.uniform(-2, 2)
            self.roll += 3.0
            # Lot balistyczny bez ciagu - akcelerometr widzi tylko opor
            # powietrza, blisko 0g (nie -1g, to nie swobodny spadek pionowy
            # w ukladzie inercjalnym czujnika).
            self.last_accel_g = -0.3

        elif t < self._t_apogee_end:
            # APOGEE - krotka faza tuz po szczycie
            self.state = 3
            self.altitude = self.APOGEE_ALT
            self.velocity = 0.0
            self.pitch = random.uniform(-15, 15)
            self.roll += 4.0
            self.last_accel_g = 0.0

        elif t < self._t_landing:
            # DESCENT - stala predkosc opadania na spadochronie, z lekkim
            # kolysaniem canopy (widoczne w pitch/roll).
            self.state = 4
            t_desc = t - self._t_apogee_end
            self.velocity = -self.DESCENT_SPEED
            self.altitude = max(self.APOGEE_ALT - self.DESCENT_SPEED * t_desc, 0.0)
            self.pitch = random.uniform(-10, 10)
            self.roll += 2.0
            # Kolysanie pod spadochronem: oscylacje wokol ~1g
            self.last_accel_g = 1.0 + 0.3 * math.sin(t_desc * 1.5) + random.uniform(-0.1, 0.1)

        else:
            # LANDED
            self.state = 5
            self.altitude = 0.0
            self.velocity = 0.0
            self.last_accel_g = 1.0

        if self.altitude < 0:
            self.altitude = 0.0

        # Degradacja baterii i szum temp
        self.voltage -= 0.0001
        self.temp += random.uniform(-0.1, 0.1)

    def generate_frame(self):
        self.update_physics()
        elapsed_ms = int((time.time() - self.start_time) * 1000)

        # Wektor przyspieszenia: kierunek z pitch/roll (jak w navballu),
        # magnitude z fazy lotu (self.last_accel_g, patrz update_physics) -
        # skalowane w przyblizonej rozdzielczosci ADXL345 (~256 LSB/g),
        # tej samej co zaklada AccelVectorWidget/telemetry.py.
        LSB_PER_G = 256.0
        p_rad = math.radians(self.pitch)
        r_rad = math.radians(self.roll)
        accel_g = getattr(self, "last_accel_g", 1.0)
        accel_lsb = accel_g * LSB_PER_G

        acc_x = int(max(-32768, min(32767, -math.sin(p_rad) * accel_lsb)))
        acc_y = int(max(-32768, min(32767, math.sin(r_rad) * math.cos(p_rad) * accel_lsb)))
        acc_z = int(max(-32768, min(32767, math.cos(r_rad) * math.cos(p_rad) * accel_lsb)))

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

        # Pakowanie ramki 50-bajtowej w 3 czesciach (mieszany byte order,
        # patrz komentarz w __init__).
        part1 = struct.pack(
            self.FRAME_FORMAT_PART1,
            ord('$'),  # B: preambula
            elapsed_ms,  # I: timestamp (big-endian)
            self.state,  # B: stan
            0,  # B: ostatnia komenda
            int(self.altitude * 10),  # h: wysokosc [dm] (big-endian)
            int(self.temp * 100),  # h: temperatura [1/100 C] (big-endian)
            0, 0, 0,  # 3xh: mag x,y,z
            acc_x, acc_y, acc_z,  # 3xh: acc x,y,z
            0, 0, 0,  # 3xh: gyro x,y,z
            1,  # B: GPS fix (symulowany fix)
            8,  # B: liczba satelitow
        )

        part2 = struct.pack(
            self.FRAME_FORMAT_PART2,
            sim_lat,  # f: GPS Lat (little-endian, jak natywny float STM32)
            sim_lon,  # f: GPS Lon
            self.altitude,  # f: GPS Alt
        )

        # Symulowany realistyczny RSSI: LoRa_getRSSI() na prawdziwym GS
        # zwraca wartosc ujemna (-164 + read), wiec symulujemy cos podobnego.
        sim_rssi = random.randint(-100, -50)
        rssi_byte = sim_rssi & 0xFF  # tak jak firmware pakuje to (uint8_t)cast

        part3 = struct.pack(
            self.FRAME_FORMAT_PART3,
            0b00000000,  # B: GPIO state (bity led_parachute..camera, patrz data_types.py)
            int(self.voltage * 100),  # H: napiecie [1/100 V] (big-endian)
            rssi_byte,  # B: RSSI (uint8, zawiera zawinieta wartosc ujemna)
            b'\n\r\0'  # 3s: zakonczenie
        )

        return part1 + part2 + part3

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
    sim = RocketSimulator(port='/dev/ttys006')
    sim.run()