"""
    case 0: brak akcji
    case 1: flight_computer->armed = 1;          // ARM
    case 2: flight_computer->armed = 0;          // DISARM
    case 3: (pusty - zarezerwowany, firmware nic nie robi)
    case 4: (pusty - zarezerwowany, firmware nic nie robi)
    case 5: flight_computer->camera = 1;         // CAMERA_ON
    case 6: flight_computer->camera = 0;         // CAMERA_OFF
    case 7: FlightComputer_fireParachute(...);   // DEPLOY_CHUTE
    case 8: (pusty - "uruchamianie startu rakiety", zarezerwowany)
    case 9: (pusty - zarezerwowany, firmware nic nie robi)
"""

COMMAND_CODES = {
    "NONE": 0,

    "ARM": 1,           # zaimplementowane w firmware (armed = 1)
    "DISARM": 2,         # zaimplementowane w firmware (armed = 0)

    "RESET": 3,          # PROWIZORYCZNIE: firmware case 3 jest pusty (no-op)
    "ABORT": 4,          # PROWIZORYCZNIE: firmware case 4 jest pusty (no-op)

    "CAMERA_ON": 5,       # zaimplementowane w firmware (camera = 1)
    "CAMERA_OFF": 6,      # zaimplementowane w firmware (camera = 0)

    "DEPLOY_CHUTE": 7,    # zaimplementowane w firmware (FlightComputer_fireParachute)

    "LAUNCH": 8,          # PROWIZORYCZNIE: firmware case 8 jest pusty (no-op),
                           # komentarz w C: "uruchamianie startu rakiety"
}

UNSUPPORTED_COMMANDS = {"TEST_BUZZER", "TEST_SERVOS"}


def resolve_command_code(name_or_code):
    if isinstance(name_or_code, int):
        if 0 <= name_or_code <= 255:
            return name_or_code, None
        return None, f"Kod komendy poza zakresem 0-255: {name_or_code}"

    text = str(name_or_code).strip()
    if not text:
        return None, "Pusta komenda."

    upper = text.upper()

    if upper in UNSUPPORTED_COMMANDS:
        return None, (
            f"Firmware GS nie ma przydzielonego kodu dla komendy '{upper}' "
            f"(brak odpowiedniego case'a w FlightComputer_handleCommand). "
            f"Nic nie wyslano."
        )

    if upper in COMMAND_CODES:
        return COMMAND_CODES[upper], None

    try:
        code = int(text, 0)
    except ValueError:
        known = ", ".join(sorted(COMMAND_CODES.keys()))
        return None, (
            f"Nieznana komenda '{text}'. Firmware oczekuje pojedynczego "
            f"bajtu - znane nazwy: {known}. Mozna tez wpisac numer (0-9)."
        )

    if 0 <= code <= 255:
        return code, None
    return None, f"Kod komendy poza zakresem 0-255: {code}"
