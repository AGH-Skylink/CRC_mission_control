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

    # Znak osi X akcelerometru (dziob rakiety) - patrz duzy komentarz przy
    # liczeniu pitch w parse_frame(). Plytka jest zamontowana "do gory
    # nogami" (obrocona o 180 stopni) wzgledem pierwotnego zalozenia, wiec
    # odwracamy znak, zeby dziob-w-gore = pitch +90. Jedyne miejsce do
    # zmiany, gdyby montaz plytki znowu sie zmienil.
    ACCEL_NOSE_SIGN = -1.0

    # Wysokosc w ramce jest liczona przez firmware wzgledem cisnienia
    # referencyjnego skalibrowanego PRZY WLACZENIU urzadzenia na ziemi
    # (patrz FlightComputer.c: pressure_reference), a NIE wzgledem poziomu
    # morza. Dlatego surowa wartosc z ramki potrafi wyjsc np. -72 m - to
    # normalne, po prostu to inny punkt odniesienia (0 = miejsce/wysokosc
    # kalibracji barometru w firmware).
    #
    # Zeby wyswietlac wysokosc zaczynajaca sie od 0 przy kazdym podlaczeniu,
    # zakotwiczamy PIERWSZY odebrany odczyt jako nowe 0 m i do wszystkich
    # kolejnych ramek doliczamy tylko DELTE zmiany wysokosci wzgledem tego
    # pierwszego odczytu (kszalt krzywej lotu zostaje dokladnie taki jak z
    # barometru, tylko przesuniety tak, ze start = 0).

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
        """Wyzeruj punkt odniesienia wysokosci - kolejna odebrana ramka
        stanie sie nowym '0 m'. Wywolywane automatycznie przy kazdym
        otwarciu portu (main.py: _on_connect), zeby pierwsza ramka nowej
        sesji zawsze startowala od 0, a nie od starego punktu zerowego z
        poprzedniego polaczenia."""
        self._altitude_baseline_raw = None

    def reset_orientation_baseline(self):
        """Wyzeruj kalibracje orientacji (pitch/roll) - kolejna odebrana
        ramka stanie sie nowym punktem odniesienia 'rakieta stoi idealnie
        pionowo, bez przechylu' (pitch=+90, roll=0).

        PO CO: akcelerometr nigdy nie da idealnie czystego odczytu z jedna
        skladowa (np. a=(285,-17,24) zamiast (285,0,0)) - male ay/az to nie
        tylko szum, ale przede wszystkim STALE niedopasowanie montazu
        czujnika w rakiecie. Bez kalibracji navball pokazywalby wiec zawsze
        odrobine niedokladny odczyt (np. pitch~84 zamiast 90) nawet gdy
        rakieta fizycznie stoi idealnie pionowo.

        ZALOZENIE (jak przy zerowaniu wysokosci): operator laczy sie z
        rakieta W MOMENCIE, gdy stoi ona pionowo na wyrzutni, gotowa do
        lotu - dokladnie tak samo jak zerowanie baroametru zaklada start z
        ziemi. Wywolywane automatycznie przy kazdym otwarciu portu
        (main.py: _on_connect)."""
        self._orientation_baseline = None

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

            altitude_relative_m = altitude_raw / 10.0   # decymetry -> metry (wzgledem kalibracji GS)

            if self._altitude_baseline_raw is None:
                self._altitude_baseline_raw = altitude_relative_m

            # Wysokosc wzgledna: pierwsza odebrana ramka (po polaczeniu /
            # reset_altitude_baseline()) = 0 m, kazda kolejna to delta
            # zmiany wzgledem niej.
            self.state.altitude = altitude_relative_m - self._altitude_baseline_raw
            # Alias - to samo co altitude, zostawione dla przejrzystosci
            # kodu/logow (above ground/launch point).
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

            # --- Orientacja (pitch/roll) z akcelerometru ---
            #
            # Uklad IMU w rakiecie: os X akcelerometru pokrywa sie z DLUGA
            # OSIA RAKIETY (dziob/silnik) - potwierdzone empirycznie: rakieta
            # stojaca pionowo na wyrzutni, gotowa do lotu, ma wektor
            # grawitacji prostopadly do ziemi i przechodzacy przez jej os
            # symetrii - czyli dokladnie przez os X akcelerometru. Odczyt w
            # tej pozycji jest wiec zdominowany przez skladowa X
            # (np. a=(285,-17,24)), a Y/Z sa bliskie zeru.
            #
            # PITCH = kat wychylenia dziobu od poziomu (-90..+90). Poprzednia
            # wersja liczyla go jako atan2(-ax, ...), co dla rakiety stojacej
            # pionowo (dziob w gore, ax dodatnie i duze) dawalo pitch ~ -90
            # stopni - navball pokazywal wtedy niemal sama "ziemie" z waskim
            # paskiem nieba, czyli odwrotnie niz powinno byc (dziob w gore =
            # navball ma pokazywac niemal samo "niebo"). Usunieto minus, zeby
            # dziob-w-gore = pitch +90 stopni.
            #
            # ROLL = obrot wokol dlugiej osi rakiety (X). Fizycznie
            # akcelerometr NIE JEST W STANIE zmierzyc tego obrotu, gdy
            # rakieta stoi (prawie) pionowo, bo wtedy wektor grawitacji lezy
            # WZDLUZ osi obrotu (X) - skladowe Y/Z, z ktorych liczylby sie
            # roll (atan2(ay,az)), sa wtedy bliskie zeru i zdominowane przez
            # SZUM CZUJNIKA (nie przez prawdziwy przechyl), co dawalo losowo
            # "skaczacy" roll (przekrzywiona drabinka na navballu mimo ze
            # rakieta stoi nieruchomo).
            #
            # Pierwsza wersja tej poprawki mrozila roll ponizej progu 15
            # (surowych jednostek) - okazalo sie za nisko: sam szum czujnika
            # w pionie daje odczyty rzedu ~30 (np. ay=-17, az=24 -> |29.4|),
            # czyli WYZEJ niz ten prog, wiec roll byl mimo wszystko liczony
            # z czystego szumu i "przekrzywial" navball. Teraz:
            #   1) prog jest wyzej (45) i jest gorna granica pelnego zaufania
            #      (90), miedzy nimi roll plynnie zanika do 0 zamiast
            #      przelaczac sie skokowo,
            #   2) ponizej progu roll DAZY DO ZERA (nie zamraza sie na
            #      przypadkowej, poprzedniej wartosci - "brak wiarygodnych
            #      danych" == zakladamy brak przechylu, a nie "cokolwiek
            #      bylo ostatnio"),
            #   3) dodatkowe wygladzanie w czasie (low-pass), zeby nawet w
            #      strefie pelnego zaufania odczyt nie skakal klatka po
            #      klatce przez szum czujnika.
            # UWAGA - fizyczny montaz plytki: plytka jest w rakiecie
            # zamontowana "do gory nogami" wzgledem tego, co pierwotnie
            # zalozylismy (obrocona o 180 stopni) - w efekcie os X
            # akcelerometru dalej pokrywa sie z dluga osia rakiety, ale ma
            # PRZECIWNY zwrot: dodatnie surowe ax odpowiada teraz dziobowi
            # w DOL, nie w gore. TelemetryParser.ACCEL_NOSE_SIGN odwraca ten
            # znak PRZED liczeniem pitch, zeby dziob-w-gore nadal dawal
            # pitch +90 (jak w komentarzu ponizej). Jesli plytke kiedys
            # zamontujecie z powrotem "jak nalezy", wystarczy zmienic ten
            # jeden znak na +1.0.
            acc = self.state.accel
            nose_accel = self.ACCEL_NOSE_SIGN * acc.x
            raw_pitch_deg = math.degrees(math.atan2(nose_accel, math.sqrt(acc.y ** 2 + acc.z ** 2 + 1e-6)))

            ROLL_NO_CONFIDENCE_RAW = 45.0   # ponizej tego roll = szum -> dazy do 0
            ROLL_FULL_CONFIDENCE_RAW = 90.0  # powyzej tego ufamy odczytowi w 100%
            ROLL_SMOOTHING = 0.25            # 0..1, wyzej = szybciej reaguje, nizej = gladsze

            horizontal_mag = math.sqrt(acc.y ** 2 + acc.z ** 2)
            raw_roll_deg = math.degrees(math.atan2(acc.y, acc.z + 1e-6))

            # Kalibracja zera (patrz reset_orientation_baseline): pierwsza
            # ramka po polaczeniu ustala, ile trzeba dodac do surowego
            # pitch/roll, zeby ta ramka odczytala sie jako "idealnie
            # pionowo, bez przechylu" (pitch=+90, roll=0). Kazda kolejna
            # ramka dostaje ten sam offset - kompensuje to stale
            # niedopasowanie montazu czujnika (np. a=(285,-17,24) zamiast
            # (285,0,0)), a nie tylko przypadkowy szum pojedynczego odczytu.
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
