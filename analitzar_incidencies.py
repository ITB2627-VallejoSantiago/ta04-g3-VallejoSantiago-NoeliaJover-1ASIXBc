import argparse
import json
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

# Compatibilitat universal de consola (Windows / Linux / macOS)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


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


def titol(text):
    print()
    print(pintar(text, "1;36"))
    print("─" * min(shutil.get_terminal_size().columns, 80))


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
    """Mostra totes les categories ordenades, sense tallar els noms."""
    titol(titol_taula)

    amplada = max(40, min(shutil.get_terminal_size().columns, 100))
    amplada_nom = amplada - 22

    print(f"{'Valor':<{amplada_nom}} {'Nombre':>8} {'%':>8}")
    print("─" * amplada)

    files = sorted(
        comptador.items(),
        key=lambda item: (-item[1], etiquetes[item[0]].casefold()),
    )

    for clau, quantitat in files:
        percentatge = quantitat / total * 100
        linies = textwrap.wrap(etiquetes[clau], width=amplada_nom)

        print(
            f"{linies[0]:<{amplada_nom}} "
            f"{quantitat:>8} {percentatge:>7.1f}%"
        )

        for linia in linies[1:]:
            print(linia)

    print("─" * amplada)
    print(f"{'TOTAL':<{amplada_nom}} {total:>8} {'100.0%':>8}")


def mostrar_resultats(registres, acceptades, descartades):
    titol("RESUM DE VALIDACIÓ")

    total = len(registres)
    percentatge = len(acceptades) / total * 100 if total else 0

    print(f"Registres llegits     : {total}")
    print(pintar(f"Registres acceptats   : {len(acceptades)}", "32"))
    print(pintar(f"Registres descartats  : {len(descartades)}", "33"))
    print(f"Percentatge acceptat  : {percentatge:.1f}%")

    if descartades:
        print("\nMotius de descart:")
        motius = Counter(
            motiu
            for _, llista in descartades
            for motiu in llista
        )
        for motiu, quantitat in motius.most_common():
            print(f"  {quantitat:>6}  {motiu}")

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
                f"  • {valor}: {maxim} "
                f"({maxim / len(acceptades) * 100:.1f}% del total acceptat)"
            )

    print("\nEls percentatges es calculen sobre les incidències acceptades.")
    print("Les opcions d'abast es compten com a categories, no com a persones.")
    print("S'agrupen espais i majúscules; no es tradueixen ni s'infereixen valors.")


def exportar_json(incidencies, ruta_json=None, mode="preguntar"):
    """
    F4: Emmagatzemar la informació en JSON (incidencies.json).
    - Comprova si el fitxer ja existeix.
    - Si no existeix: el crea amb totes les incidències noves.
    - Si ja existeix: demana si sobreescriure o afegir sense duplicats per ID.
    mode pot ser:
      - 'preguntar': demana interactivament a la consola.
      - 'overwrite': sobreescriu directament.
      - 'append': afegeix conservant existents i evitant duplicats per ID.
    """
    if ruta_json is None:
        ruta_json = CARPETA / "incidencies.json"
    else:
        ruta_json = Path(ruta_json)

    # Assegurar que cada incidència té un ID assignat
    registres_amb_id = []
    for idx, inc in enumerate(incidencies, start=1):
        item = dict(inc)
        if "id" not in item or not item["id"]:
            item["id"] = f"INC-{idx:04d}"
        registres_amb_id.append(item)

    fitxer_existeix = ruta_json.exists()

    if fitxer_existeix:
        if mode == "preguntar":
            titol("F4: EMMAGATZEMAR EN JSON (incidencies.json)")
            print(f"El fitxer '{ruta_json.name}' ja existeix.")
            print("Què vols fer?")
            print("  [1] Sobreescriure'l (esborra contingut anterior i escriu tot de nou)")
            print("  [2] Afegir les noves incidències (conserva existents i evita duplicats per ID)")
            print("  [0] Cancel·lar operació")
            opcio = input("Tria una opció (1/2/0): ").strip()
            if opcio == "1":
                accio = "overwrite"
            elif opcio == "2":
                accio = "append"
            else:
                print("Operació d'emmagatzematge JSON cancel·lada.")
                return None
        else:
            accio = mode
    else:
        accio = "overwrite"

    if accio == "overwrite" or not fitxer_existeix:
        with open(ruta_json, "w", encoding="utf-8") as f:
            json.dump(registres_amb_id, f, indent=2, ensure_ascii=False)
        resultat = {
            "accio": "overwrite",
            "fitxer": str(ruta_json),
            "total_desats": len(registres_amb_id),
            "afegits": len(registres_amb_id),
            "duplicats_ignorats": 0,
        }
    elif accio == "append":
        try:
            with open(ruta_json, "r", encoding="utf-8") as f:
                existents = json.load(f)
                if not isinstance(existents, list):
                    existents = []
        except Exception:
            existents = []

        ids_existents = {
            str(item.get("id")) for item in existents if isinstance(item, dict) and "id" in item
        }
        claus_existents = {
            tuple(str(item.get(c, "")).strip() for c in CAMPS)
            for item in existents if isinstance(item, dict)
        }

        nous_afegits = 0
        duplicats = 0
        max_num = len(existents)

        for item in registres_amb_id:
            clau = tuple(str(item.get(c, "")).strip() for c in CAMPS)
            if str(item.get("id")) in ids_existents or clau in claus_existents:
                duplicats += 1
            else:
                max_num += 1
                item_copia = dict(item)
                item_copia["id"] = f"INC-{max_num:04d}"
                existents.append(item_copia)
                ids_existents.add(item_copia["id"])
                claus_existents.add(clau)
                nous_afegits += 1

        with open(ruta_json, "w", encoding="utf-8") as f:
            json.dump(existents, f, indent=2, ensure_ascii=False)

        resultat = {
            "accio": "append",
            "fitxer": str(ruta_json),
            "total_desats": len(existents),
            "afegits": nous_afegits,
            "duplicats_ignorats": duplicats,
        }

    return resultat


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
    parser.add_argument(
        "--export-json",
        action="store_true",
        help="Executa F4: exporta les incidències a incidencies.json.",
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
        titol("ANÀLISI D'INCIDÈNCIES")
        print(f"Fitxer: {args.xml.expanduser().resolve()}")
        print(
            "Dates amb barres: "
            + ("mes/dia/any" if args.ordre_data == "mdy" else "dia/mes/any")
        )
        print("Criteri de descripció: mínim 15 caràcters i text no genèric.")

        registres = llegir_xml(args.xml.expanduser())
        acceptades, descartades = validar_registres(
            registres, args.ordre_data
        )
        mostrar_resultats(registres, acceptades, descartades)

        titol("DADES I INFORMACIÓ")
        print("Dada: el dispositiu indicat en una incidència.")
        print("Informació: quants incidents afecten cada tipus de dispositiu.")

        if args.export_json:
            res_json = exportar_json(acceptades, mode="preguntar")
            if res_json:
                print(pintar(f"\n[OK] Fitxer JSON actualitzat: {res_json['fitxer']}", "32"))
                print(f"     Mode: {res_json['accio']} | Afegits: {res_json['afegits']} | Total registres: {res_json['total_desats']}")

        print(f"\nTemps d'execució: {perf_counter() - inici:.3f} segons.")
        print("Anàlisi completada.")
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
