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

    altitude: float = 0.0
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

    @property
    def pyro1(self) -> bool: return bool(self.gpio_state & (1 << 0))

    @property
    def pyro2(self) -> bool: return bool(self.gpio_state & (1 << 1))

    @property
    def led_r(self) -> bool: return bool(self.gpio_state & (1 << 2))

    @property
    def led_g(self) -> bool: return bool(self.gpio_state & (1 << 3))

    @property
    def led_b(self) -> bool: return bool(self.gpio_state & (1 << 4))

    @property
    def buzzer(self) -> bool: return bool(self.gpio_state & (1 << 5))

    @property
    def camera(self) -> bool: return bool(self.gpio_state & (1 << 6))

    @property
    def breakaway_wire(self) -> bool: return bool(self.gpio_state & (1 << 7))