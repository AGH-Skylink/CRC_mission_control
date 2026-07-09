import math
import dearpygui.dearpygui as dpg
import ui.theme as theme


class AccelVectorWidget:
    """Widget 3D (rzut izometryczny na drawlist) pokazujacy wektor
    przyspieszenia (accel x,y,z) z ramki telemetrii. DearPyGui w tej
    wersji nie ma natywnego wykresu 3D, wiec robimy rzut recznie - tak
    samo jak navball.py robi to dla poziomicy.

    WAZNE (oriencja osi): os X akcelerometru pokrywa sie z DLUGA OSIA
    RAKIETY (patrz core/telemetry.py) - rakieta stojaca pionowo na
    wyrzutni daje odczyt zdominowany przez skladowa X, a Y/Z sa bliskie
    zeru. Poprzednia wersja tego widgetu rzutowala akcelerometr 1:1 na
    lokalne osie rysunku (x->"x" izometrii, y->"y" izometrii), gdzie
    "y" izometrii to jedyna os pionowa na ekranie - w efekcie dla
    stojacej pionowo rakiety wektor wychodzil na ukos (bo dominowala
    skladowa X, rzutowana na przekatna), zamiast prosto w gore. Teraz
    zamieniamy role osi tak, zeby akcelerometr-X (dziob rakiety) byl
    rzutowany na PIONOWA os widgetu - dla rakiety stojacej pionowo
    wektor bedzie wskazywal prosto w gore, tak jak w rzeczywistosci.

    Ulepszenia wzgledem pierwszej wersji (dla czytelnosci):
      - siatka "podlogi" (plaszczyzna X-Z) daje poczucie glebi/perspektywy
      - pierscienie odniesienia (1g / 2g) na plaszczyznie podlogi, zeby
        latwiej ocenic magnitude na oko
      - osie sa cienkie/przygaszone (tlo), wektor jest gruby i jaskrawy
        z kulka na koncu, wiec od razu przyciaga wzrok
      - etykieta z komponentami x,y,z i magnitude jest zawsze czytelna
    """

    # Przyblizona skala ADXL345 w trybie pelnej rozdzielczosci (+-2g):
    # ok. 256 LSB/g. Sluzy tylko do ladnego skalowania i etykiety "w g" -
    # nie jest to kalibracja firmware, tylko orientacyjny odczyt.
    LSB_PER_G = 256.0

    def __init__(self, parent_tag, width=300, height=300):
        self.width = width
        self.height = height
        self.cx = width / 2
        # Origin przesuniety w dol, zeby zostawic miejsce nad nim na
        # wektor wskazujacy w gore (typowy przypadek: rakieta stoi pionowo,
        # ~1g wzdluz jej dlugiej osi / akcelerometr-X).
        self.cy = height * 0.7
        # Wieksza skala niz na starcie projektu: wiemy juz z raportu
        # koncowego, ze rakieta ma stosunkowo skromne mozliwosci
        # przyspieszenia (szczyt ~104 m/s^2 / ~10.6g tylko przy starcie
        # silnika, reszta lotu to ~0-1.3g), wiec mozemy sobie pozwolic na
        # wieksza, czytelniejsza strzalke bez ryzyka, ze normalny odczyt
        # (1g w spoczynku/pod spadochronem) bedzie ledwo widoczny. Wartosci
        # dobrane tak, by przy tym rozmiarze widgetu (300x300) wektor sie
        # nie "wyjezdzal" poza canvas nawet gdy wskazuje prosto w gore.
        self.axis_len = 80       # dlugosc osi referencyjnych w pikselach (1g)
        self.max_vec_len = 170   # maksymalna dlugosc rysowanego wektora

        self.vector_tag = dpg.generate_uuid()
        self.tip_dot_tag = dpg.generate_uuid()
        self.label_tag = dpg.generate_uuid()

        self._build_ui(parent_tag)

    def _iso_project(self, x, y, z):
        """Rzut izometryczny widgetu: lokalne 'x' w prawo-dol, lokalne
        'y' w gore (jedyna os obrazu ktora jest czysto pionowa), lokalne
        'z' w lewo-gora. UWAGA: to sa lokalne osie RYSUNKU, nie osie
        akcelerometru wprost - patrz komentarz w update()."""
        cos30 = math.cos(math.radians(30))
        sin30 = math.sin(math.radians(30))
        sx = self.cx + (x - z) * cos30
        sy = self.cy - y - (x + z) * sin30
        return sx, sy

    def _draw_floor_grid(self, half_extent_units, step_units, unit_px):
        """Siatka na plaszczyznie lokalnej x-z (y=0), daje poczucie perspektywy."""
        grid_color = (60, 60, 60)
        n = int(half_extent_units / step_units)
        for i in range(-n, n + 1):
            x = i * step_units * unit_px
            p1 = self._iso_project(x, 0, -half_extent_units * unit_px)
            p2 = self._iso_project(x, 0, half_extent_units * unit_px)
            dpg.draw_line(p1, p2, color=grid_color, thickness=1)

            z = i * step_units * unit_px
            p3 = self._iso_project(-half_extent_units * unit_px, 0, z)
            p4 = self._iso_project(half_extent_units * unit_px, 0, z)
            dpg.draw_line(p3, p4, color=grid_color, thickness=1)

    def _draw_reference_ring(self, radius_px, color):
        """Przyblizony 'pierscien' 1g/2g na plaszczyznie podlogi (elipsa
        zlozona z krotkich odcinkow, zeby dobrze wygladala po rzucie)."""
        pts = []
        segments = 40
        for i in range(segments + 1):
            ang = 2 * math.pi * i / segments
            x = radius_px * math.cos(ang)
            z = radius_px * math.sin(ang)
            pts.append(self._iso_project(x, 0, z))
        for p1, p2 in zip(pts, pts[1:]):
            dpg.draw_line(p1, p2, color=color, thickness=1)

    def _build_ui(self, parent_tag):
        with dpg.drawlist(width=self.width, height=self.height, parent=parent_tag):
            dpg.draw_rectangle((0, 0), (self.width, self.height), color=theme.COLOR_BLACK, fill=theme.COLOR_BLACK)

            unit_px = self.axis_len  # 1 jednostka siatki = dlugosc osi
            self._draw_floor_grid(half_extent_units=2, step_units=1, unit_px=unit_px / 2)
            self._draw_reference_ring(unit_px, theme.ACCENT_TRANS[:3] if len(theme.ACCENT_TRANS) == 4 else theme.ACCENT_TRANS)
            self._draw_reference_ring(unit_px * 2, (50, 50, 50))

            origin = self._iso_project(0, 0, 0)

            # Osie referencyjne - cienkie i przygaszone, zeby nie
            # konkurowaly wizualnie z wektorem przyspieszenia.
            # Lokalna os "y" widgetu (pionowa na ekranie) odpowiada
            # akcelerometrowi-X (dlugiej osi rakiety) - patrz update().
            x_end = self._iso_project(self.axis_len, 0, 0)
            y_end = self._iso_project(0, self.axis_len, 0)
            z_end = self._iso_project(0, 0, self.axis_len)

            dpg.draw_arrow(x_end, origin, color=(180, 70, 70), thickness=1, size=6)
            dpg.draw_arrow(y_end, origin, color=(70, 160, 70), thickness=1, size=6)
            dpg.draw_arrow(z_end, origin, color=(70, 110, 200), thickness=1, size=6)

            # Etykiety: "Y" to zawsze pionowa os widgetu (wysokosc/gora na
            # ekranie) - konwencja niezalezna od tego, ktory kanal
            # akcelerometru akurat do niej trafia (patrz update()). "X" to
            # druga poziomo-skosna os, "Z" trzecia.
            dpg.draw_text((x_end[0] + 4, x_end[1]), "X", color=(220, 100, 100), size=13)
            dpg.draw_text((y_end[0] + 4, y_end[1] - 14), "Y", color=(100, 220, 100), size=13)
            dpg.draw_text((z_end[0] - 14, z_end[1]), "Z", color=(100, 150, 230), size=13)

            dpg.draw_circle(origin, 3, color=theme.TEXT_NORMAL, fill=theme.TEXT_NORMAL)

            # Wektor przyspieszenia - gruby, jaskrawy, z kulka na koncu
            dpg.draw_arrow(origin, origin, color=theme.STATUS_AMBER, thickness=6, size=18, tag=self.vector_tag)
            dpg.draw_circle(origin, 8, color=theme.STATUS_AMBER, fill=theme.STATUS_AMBER, tag=self.tip_dot_tag)

            dpg.draw_text(
                (6, self.height - 34),
                "a = (0, 0, 0)\n|a| = 0.00 g",
                color=theme.STATUS_AMBER, size=13, tag=self.label_tag,
            )

    def update(self, ax: float, ay: float, az: float):
        mag_raw = math.sqrt(ax * ax + ay * ay + az * az)
        mag_g = mag_raw / self.LSB_PER_G

        if mag_raw > 1e-6:
            # 1g ma miec dlugosc ~axis_len, ale ograniczamy maks. dlugosc,
            # zeby bardzo duze udary (np. odpalenie pirotechniki) nie
            # wyjezdzaly poza widget.
            length_px = min((mag_raw / self.LSB_PER_G) * self.axis_len, self.max_vec_len)
            k = length_px / mag_raw
        else:
            k = 0.0

        origin = self._iso_project(0, 0, 0)
        # Zamiana osi: akcelerometr-X (dluga os rakiety, dziob) trafia na
        # PIONOWA os widgetu (etykieta "Y" - Y = wysokosc/gora na ekranie,
        # zawsze), akcelerometr-Y na skosna os "X", akcelerometr-Z zostaje
        # jako "Z". To odzwierciedla rzeczywisty uklad IMU: gdy rakieta
        # stoi pionowo na wyrzutni gotowa do lotu, wektor grawitacji jest
        # prostopadly do ziemi i przechodzi przez os symetrii rakiety, czyli
        # akcelerometr-X - dlatego to ax musi sterowac pionowa osia widgetu,
        # a nie ay (mimo ze ta os na ekranie zawsze nazywa sie "Y").
        tip = self._iso_project(ay * k, ax * k, az * k)

        dpg.configure_item(self.vector_tag, p1=origin, p2=tip)
        dpg.configure_item(self.tip_dot_tag, center=tip)
        dpg.configure_item(
            self.label_tag,
            text=f"a = ({ax:.0f}, {ay:.0f}, {az:.0f})\n|a| = {mag_g:.2f} g",
        )
