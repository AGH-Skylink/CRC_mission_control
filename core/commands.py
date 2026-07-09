"""
Mapowanie nazw komend uzywanych w UI Mission Control na pojedyncze bajty,
DOKLADNIE zgodne ze switchem w FlightComputer_handleCommand() w firmware
ground station (AGH-Skylink/CRC-LoRa, branch Pirx,
OldAvio/Core/Src/FlightComputer.c, linie ~540-573):

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

Firmware odbiera to jako JEDEN surowy bajt (LoRa_receive(...,1)), nie tekst -
patrz core/serial_manager.py: send_command_byte().

WAZNE: kody 0, 3, 4, 8, 9 sa w firmware pustymi/no-opowymi galeziami switcha.
Wysylajac je NIC sie nie stanie po stronie rakiety, dopoki zespol
avioniki nie zaimplementuje tam faktycznej logiki. Nazwy RESET/ABORT/LAUNCH
ponizej to PROWIZORYCZNE, udokumentowane przypisania do wolnych slotow -
latwo je podmienic w jednym miejscu (ten slownik), gdy firmware bedzie
gotowy.

Komendy z UI (TEST_BUZZER, TEST_SERVOS), dla ktorych firmware NIE ma zadnego
przydzielonego kodu (nawet pustego), NIE sa tu mapowane celowo - wysylanie
dla nich losowego/nieprzypisanego bajtu byloby myslace, wiec panel powinien
je zablokowac z czytelnym komunikatem zamiast zgadywac kod.
"""

# Nazwa komendy (z przyciskow/sekwencji w UI) -> kod bajtu wysylany do GS.
# Klucze porownywane case-insensitive (patrz resolve_command_code()).
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

# Komendy uzywane w UI (main.py: self.sequences), dla ktorych firmware NIE MA
# zadnego przydzielonego kodu - jawnie wypisane, zeby bylo widac, ze to nie
# przeoczenie.
UNSUPPORTED_COMMANDS = {"TEST_BUZZER", "TEST_SERVOS"}


def resolve_command_code(name_or_code):
    """Zamien nazwe komendy (np. "ARM") albo numer (np. "7", "0x07", 7) na
    kod bajtu 0-255 do wyslania przez send_command_byte().

    Zwraca (code:int, warning:str|None). Jesli komenda jest nieznana lub
    jawnie niewspierana przez firmware, code=None i warning zawiera powod -
    UI powinno wtedy NIE wysylac niczego i pokazac ten komunikat userowi."""

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

    # Pozwol tez wpisac numer bezposrednio (np. do testow / debugowania):
    # "7", "0x07" itp.
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
