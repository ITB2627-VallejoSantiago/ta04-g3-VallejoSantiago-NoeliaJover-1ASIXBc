#!/usr/bin/env python3
"""Analitzador visual d’incidències. Python 3, sense dependències externes."""

import argparse
import os
import shutil
import sys
import textwrap
import unicodedata
import xml.etree.ElementTree as ET

from collections import Counter
from datetime import datetime
from pathlib import Path
from time import perf_counter


CARPETA = Path(__file__).resolve().parent

CAMPS = (
    "data", "nom", "lloc", "departament", "dispositiu",
    "equip", "categoria", "descripcio", "impacte", "abast",
)

ESTADISTIQUES = {
    "categoria": "INCIDÈNCIES PER CATEGORIA",
    "departament": "INCIDÈNCIES PER DEPARTAMENT",
    "dispositiu": "INCIDÈNCIES PER DISPOSITIU",
    "impacte": "IMPACTE SOBRE EL TREBALL",
    "abast": "ABAST: USUARIS AFECTATS",
}

DESCRIPCIONS_GENERIQUES = {
    "no funciona", "no funciona bé", "no funciona be",
    "ayuda por favor", "it is broken", "no lo sé",
    "no ho sé", "error", "test", "prova",
}

COLOR = False


def pintar(text, codi):
    """Aplica color només quan la sortida és una terminal compatible."""
    return f"\033[{codi}m{text}\033[0m" if COLOR else str(text)


def netejar(text):
    """Unifica espais i representació Unicode sense inventar dades."""
    return unicodedata.normalize("NFC", " ".join((text or "").split()))


def amplada_terminal():
    return max(24, min(shutil.get_terminal_size().columns, 108))


def segur(text):
    # Evita que dades XML injectin seqüències de control a la terminal.
    return "".join(c for c in str(text) if unicodedata.category(c) not in ("Cc", "Cf"))


def panell(linies, color="36"):
    ample = amplada_terminal() - 4
    print(pintar("╭" + "─" * (ample + 2) + "╮", color))
    for text in linies:
        for linia in textwrap.wrap(segur(text), width=ample) or [""]:
            print(pintar("│ ", color) + linia.ljust(ample) + pintar(" │", color))
    print(pintar("╰" + "─" * (ample + 2) + "╯", color))


def titol(text):
    print()
    for linia in textwrap.wrap(segur(text), width=amplada_terminal() - 4):
        print(pintar("  " + linia, "1;96"))
    print(pintar("─" * amplada_terminal(), "2;36"))


def capcalera(ruta, ordre):
    print()
    panell([
        "I N C I D E N T   /   L A B",
        "CENTRE D’ANÀLISI · XML → INFORMACIÓ",
        "",
        "Validació de dades  /  Distribucions  /  Indicadors",
    ], "1;95")
    print()
    panell([
        "FITXER  ·  " + str(ruta.expanduser().resolve()),
        "DATES   ·  " + ("mes/dia/any" if ordre == "mdy" else "dia/mes/any"),
        "CRITERI ·  Descripció de mínim 15 caràcters i text no genèric.",
    ], "36")


def targetes(elements):
    ample = amplada_terminal()
    if ample < 76:
        for etiqueta, valor, color in elements:
            panell([etiqueta, str(valor)], color)
        return
    mida = (ample - 3) // 4
    for tipus in ("top", "label", "value", "bottom"):
        parts = []
        for etiqueta, valor, color in elements:
            interior = mida - 4
            if tipus == "top":
                bloc = "╭" + "─" * (mida - 2) + "╮"
            elif tipus == "bottom":
                bloc = "╰" + "─" * (mida - 2) + "╯"
            else:
                contingut = etiqueta if tipus == "label" else str(valor)
                bloc = "│ " + contingut.center(interior) + " │"
            parts.append(pintar(bloc, color))
        print(" ".join(parts))


def llegir_xml(ruta):
    """Llegeix totes les incidències i comprova l'estructura XML."""
    arrel = ET.parse(ruta).getroot()

    if arrel.tag != "incidencies":
        raise ValueError("L'arrel del document ha de ser <incidencies>.")

    registres = []

    for numero, element in enumerate(arrel, start=1):
        etiquetes = [camp.tag for camp in element]

        if (
            element.tag != "incidencia"
            or len(etiquetes) != len(CAMPS)
            or set(etiquetes) != set(CAMPS)
            or any(len(camp) for camp in element)
        ):
            raise ValueError(
                f"Estructura incorrecta al registre {numero}. "
                "Cal una <incidencia> amb les 10 etiquetes esperades, "
                "sense camps repetits ni elements interns."
            )

        registres.append({
            camp.tag: netejar(camp.text)
            for camp in element
        })

    return registres


def interpretar_data(text, ordre):
    """Valida la data completa, no només l'any."""
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        pass

    base = "%m/%d/%Y" if ordre == "mdy" else "%d/%m/%Y"

    for format_data in (base + " %H:%M:%S", base + " %H:%M", base):
        try:
            return datetime.strptime(text, format_data).date()
        except ValueError:
            pass

    return None


def validar_registres(registres, ordre):
    """Exclou registres incorrectes i conserva els seus motius en memòria."""
    acceptades = []
    descartades = []
    vistes = set()
    avui = datetime.now().date()

    for numero, dades in enumerate(registres, start=1):
        motius = []
        data = interpretar_data(dades["data"], ordre)

        if data is None:
            motius.append("Data buida o invàlida")
        elif data > avui:
            motius.append("Data futura")

        if not dades["nom"]:
            motius.append("Nom buit")

        descripcio = dades["descripcio"]

        if len(descripcio) < 15:
            motius.append("Descripció de menys de 15 caràcters")
        elif descripcio.casefold() in DESCRIPCIONS_GENERIQUES:
            motius.append("Descripció genèrica")

        # Duplicat complet: inclou també la data i l'hora originals.
        clau = tuple(dades[camp] for camp in CAMPS)

        if clau in vistes:
            motius.append("Registre duplicat")

        if motius:
            descartades.append((numero, motius))
        else:
            vistes.add(clau)
            acceptades.append(dades)

    return acceptades, descartades


def calcular_estadistiques(incidencies):
    """Compta les cinc distribucions en una sola passada."""
    comptadors = {camp: Counter() for camp in ESTADISTIQUES}
    etiquetes = {camp: {} for camp in ESTADISTIQUES}

    for incidencia in incidencies:
        for camp in ESTADISTIQUES:
            valor = incidencia[camp]

            # None representa un camp buit.
            # casefold agrupa diferències de majúscules/minúscules.
            clau = valor.casefold() if valor else None
            comptadors[camp][clau] += 1
            etiquetes[camp].setdefault(clau, valor or "(Sense informar)")

    return comptadors, etiquetes


def mostrar_taula(titol_taula, comptador, etiquetes, total):
    """Distribució completa amb barres proporcionals i noms sense truncar."""
    titol(titol_taula)
    ample = amplada_terminal()
    colors = ("96", "95", "94", "92", "93")
    files = sorted(comptador.items(), key=lambda x: (-x[1], etiquetes[x[0]].casefold()))
    mida_barra = max(5, ample - 24)
    for index, (clau, quantitat) in enumerate(files):
        color = colors[index % len(colors)]
        percentatge = quantitat / total * 100 if total else 0
        for linia in textwrap.wrap(segur(etiquetes[clau]), width=ample - 4):
            print("  " + pintar(linia, "1;" + color))
        plena = round(mida_barra * percentatge / 100)
        barra = pintar("█" * plena, color) + pintar("░" * (mida_barra - plena), "2;37")
        print("  " + barra + pintar(f" {quantitat:>6}  {percentatge:5.1f}%", "1;97"))
        print()
    print(pintar(f"  TOTAL · {total} incidències · " + ("100.0%" if total else "0.0%"), "1;96"))


def mostrar_resultats(registres, acceptades, descartades):
    titol("RESUM DE VALIDACIÓ")

    total = len(registres)
    percentatge = len(acceptades) / total * 100 if total else 0

    targetes([
        ("LLEGITS", total, "1;94"),
        ("ACCEPTATS", len(acceptades), "1;92"),
        ("DESCARTATS", len(descartades), "1;93"),
        ("ACCEPTACIÓ", f"{percentatge:.1f}%", "1;95"),
    ])
    ample = amplada_terminal() - 4
    plena = round(ample * percentatge / 100)
    print()
    print("  " + pintar("█" * plena, "92") + pintar("░" * (ample - plena), "33"))
    print(pintar("  Acceptats / descartats", "2;37"))

    if descartades:
        print("\nMotius de descart:")
        motius = Counter(
            motiu
            for _, llista in descartades
            for motiu in llista
        )
        for motiu, quantitat in motius.most_common():
            print(pintar(f"  ◆ {quantitat:>6}  {motiu}", "93"))

        print("\nUn registre pot tenir més d'un motiu.")
        print("Exemples de registres descartats (posició dins de l'XML):")
        for numero, errors in descartades[:5]:
            print(f"  #{numero}: {'; '.join(errors)}")

    if not acceptades:
        print("\nNo hi ha incidències acceptades per calcular estadístiques.")
        return

    comptadors, etiquetes = calcular_estadistiques(acceptades)

    for camp, nom in ESTADISTIQUES.items():
        mostrar_taula(
            nom, comptadors[camp], etiquetes[camp], len(acceptades)
        )

    titol("INFORMACIÓ DESTACADA")

    for camp, nom in (
        ("categoria", "Categoria més freqüent"),
        ("departament", "Departament amb més incidències"),
    ):
        conegudes = {
            clau: quantitat
            for clau, quantitat in comptadors[camp].items()
            if clau is not None
        }

        if not conegudes:
            print(f"{nom}: sense dades informades.")
            continue

        maxim = max(conegudes.values())
        guanyadores = [
            etiquetes[camp][clau]
            for clau, quantitat in conegudes.items()
            if quantitat == maxim
        ]

        print(f"{nom}:")
        for valor in sorted(guanyadores):
            print(
                f"  ◆ {segur(valor)}: {maxim} "
                f"({maxim / len(acceptades) * 100:.1f}% del total acceptat)"
            )

    print("\nEls percentatges es calculen sobre les incidències acceptades.")
    print("Les opcions d'abast es compten com a categories, no com a persones.")
    print("S'agrupen espais i majúscules; no es tradueixen ni s'infereixen valors.")


def main():
    global COLOR

    parser = argparse.ArgumentParser(
        description="Llegeix un XML d'incidències i mostra estadístiques."
    )
    parser.add_argument(
        "xml",
        nargs="?",
        type=Path,
        default=CARPETA / "incidencies_filtrades.xml",
        help="Ruta de l'XML. Per defecte: incidencies_filtrades.xml.",
    )
    parser.add_argument(
        "--ordre-data",
        choices=("mdy", "dmy"),
        default="mdy",
        help="mdy: mes/dia/any; dmy: dia/mes/any. Per defecte: mdy.",
    )
    parser.add_argument(
        "--sense-color",
        action="store_true",
        help="Desactiva els colors.",
    )
    args = parser.parse_args()

    COLOR = (
        sys.stdout.isatty()
        and not args.sense_color
        and "NO_COLOR" not in os.environ
        and os.environ.get("TERM") != "dumb"
    )

    inici = perf_counter()

    try:
        capcalera(args.xml, args.ordre_data)

        registres = llegir_xml(args.xml.expanduser())
        acceptades, descartades = validar_registres(
            registres, args.ordre_data
        )
        mostrar_resultats(registres, acceptades, descartades)

        titol("DADES I INFORMACIÓ")
        print("Dada: el dispositiu indicat en una incidència.")
        print("Informació: quants incidents afecten cada tipus de dispositiu.")

        print()
        panell([
            "✓ ANÀLISI COMPLETADA",
            f"Temps d’execució: {perf_counter() - inici:.3f} segons",
            "Lectura finalitzada. No s’ha modificat cap fitxer XML.",
        ], "1;92")
        return 0

    except FileNotFoundError:
        print(pintar(f"\nERROR: no es troba {args.xml}", "31"), file=sys.stderr)
    except ET.ParseError as error:
        print(
            pintar(f"\nERROR: XML mal format: {error}", "31"),
            file=sys.stderr,
        )
    except (OSError, ValueError) as error:
        print(pintar(f"\nERROR: {error}", "31"), file=sys.stderr)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
