from dataclasses import dataclass, field
from enum import Enum, IntEnum


class MissionState(IntEnum):
    IDLE = 0
    LAUNCH = 1
    ASCENT = 2
    APOGEE = 3
    DESCENT = 4
    LANDING = 5
    EMERGENCY = 6


class ConnectionStatus(Enum):
    DISCONNECTED = (0, 0, 0)
    CONNECTED = (0, 255, 0)
    ERROR = (255, 0, 0)
    DROPPED_FRAMES = (255, 191, 0)
    DATA_RECEIVING = (0, 0, 255)


@dataclass
class Vector3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass
class TelemetryFrame:
    timestamp_ms: int = 0
    state: MissionState = MissionState.IDLE
    last_command: int = 0

    altitude: float = 0.0       # przyblizona wysokosc n.p.m. (patrz telemetry.py: LAUNCH_SITE_ELEVATION_M + delta)
    altitude_agl: float = 0.0   # surowa delta wzgledem pierwszego odczytu barometru (above launch point)
    temp: float = 0.0

    accel: Vector3 = field(default_factory=Vector3)
    gyro: Vector3 = field(default_factory=Vector3)
    mag: Vector3 = field(default_factory=Vector3)

    gps_fix: int = 0
    gps_sats: int = 0
    gps_lat: float = 0.0
    gps_lon: float = 0.0
    gps_alt: float = 0.0

    gpio_state: int = 0
    voltage: float = 0.0
    rssi: int = 0

    pitch: float = 0.0
    roll: float = 0.0
    yaw: float = 0.0

    last_update: float = field(default_factory=lambda: 0.0)
    dropped_frames: int = 0

    # Bity GPIO (bajt 43 ramki) - zweryfikowane wprost w kodzie ground
    # station (AGH-Skylink/CRC-LoRa, branch Pirx, FlightComputer.c,
    # sekcja "GPIO STATUS"). Poprzednia wersja mapowala te bity zupelnie
    # inaczej (pyro1/pyro2/led_r/led_g/led_b/buzzer/camera/breakaway_wire
    # kolejno od bitu 0) - nie odpowiadalo to temu, co faktycznie wysyla
    # firmware. Prawdziwa kolejnosc (MSB -> LSB):
    #   bit7: led_parachute, bit6: led_state, bit5: led_r, bit4: led_g,
    #   bit3: led_b, bit2: led_y, bit1: buzzer, bit0: camera

    @property
    def led_parachute(self) -> bool: return bool(self.gpio_state & (1 << 7))

    @property
    def led_state(self) -> bool: return bool(self.gpio_state & (1 << 6))

    @property
    def led_r(self) -> bool: return bool(self.gpio_state & (1 << 5))

    @property
    def led_g(self) -> bool: return bool(self.gpio_state & (1 << 4))

    @property
    def led_b(self) -> bool: return bool(self.gpio_state & (1 << 3))

    @property
    def led_y(self) -> bool: return bool(self.gpio_state & (1 << 2))

    @property
    def buzzer(self) -> bool: return bool(self.gpio_state & (1 << 1))

    @property
    def camera(self) -> bool: return bool(self.gpio_state & (1 << 0))

    # Aliasy zachowane dla wstecznej kompatybilnosci z UI, ktore uzywalo
    # nazw pyro1/pyro2 - w firmware te piny nazywaja sie led_parachute i
    # led_state, wiec podpinamy je pod prawidlowe bity zamiast (blednych)
    # bitow 0 i 1.
    @property
    def pyro1(self) -> bool: return self.led_parachute

    @property
    def pyro2(self) -> bool: return self.led_state

    @property
    def breakaway_wire(self) -> bool:
        # UWAGA: firmware GS SLEDZI stan zerwania linki (breakaway_wire_detached)
        # wewnetrznie, ale NIE wysyla go obecnie w ramce telemetrii (nie ma go
        # w bajcie GPIO ani nigdzie indziej w telemetry_frame). Poprzednia
        # wersja czytala to z bitu 7 gpio_state, co w rzeczywistosci jest
        # bitem led_parachute - dawalo to fikcyjne/losowe wskazanie. Dopoki
        # firmware nie zacznie tego faktycznie wysylac, zwracamy zawsze
        # False (i UI powinno to oznaczac jako "N/A", nie jako realny odczyt).
        return False
