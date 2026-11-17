import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

CARPETA = Path(__file__).resolve().parent

# Mes/día/año: 11/3/2026 significa 3 de noviembre.
# Si tu CSV usa día/mes/año, cambia a "%d/%m/%Y".
FORMATO_FECHA = "%m/%d/%Y"

ETIQUETAS = {
    "data", "nom", "lloc", "departament", "dispositiu",
    "equip", "categoria", "descripcio", "impacte", "abast",
}


def leer_fecha(texto):
    for formato in (
        FORMATO_FECHA + " %H:%M:%S",
        FORMATO_FECHA + " %H:%M",
        FORMATO_FECHA,
    ):
        try:
            return datetime.strptime(texto, formato)
        except ValueError:
            pass

    try:
        return datetime.fromisoformat(texto)
    except ValueError:
        return None


def guardar(raiz, nombre):
    arbol = ET.ElementTree(raiz)
    ET.indent(arbol, space="  ")
    arbol.write(
        CARPETA / nombre,
        encoding="utf-8",
        xml_declaration=True,
    )


def main():
    raiz = ET.parse(CARPETA / "incidencies.xml").getroot()

    if raiz.tag != "incidencies":
        raise ValueError("La raíz debe ser <incidencies>.")

    aceptadas = ET.Element("incidencies")
    descartadas = ET.Element("incidencies")
    vistas = set()

    for incidencia in raiz:
        if (
            incidencia.tag != "incidencia"
            or len(incidencia) != len(ETIQUETAS)
            or {campo.tag for campo in incidencia} != ETIQUETAS
            or any(len(campo) for campo in incidencia)
        ):
            raise ValueError(
                "Estructura incorrecta. Ejecuta primero csv_a_xml.py."
            )

        datos = {
            campo.tag: " ".join((campo.text or "").split())
            for campo in incidencia
        }

        motivos = []
        fecha = leer_fecha(datos["data"])
        descripcion = datos["descripcio"]

        if fecha is None:
            motivos.append("Fecha vacía o inválida")
        elif fecha.date() > datetime.now().date():
            motivos.append("Fecha futura")

        if not datos["nom"]:
            motivos.append("Nombre vacío")

        if len(descripcion) < 15 or descripcion.casefold() in {
            "no funciona", "no funciona bé", "no funciona be",
            "ayuda por favor", "it is broken", "no lo sé",
            "no ho sé", "error", "test", "prova",
        }:
            motivos.append("Descripción insuficiente")

        # Compara todos los campos, incluida la fecha.
        clave = tuple(sorted(datos.items()))

        if clave in vistas:
            motivos.append("Registro duplicado")

        if motivos:
            incidencia.set("motivo_descarte", "; ".join(motivos))
            descartadas.append(incidencia)
        else:
            vistas.add(clave)
            aceptadas.append(incidencia)

    guardar(aceptadas, "incidencies_filtrades.xml")
    guardar(descartadas, "incidencies_descartades.xml")

    print(f"Total: {len(raiz)}")
    print(f"Aceptadas: {len(aceptadas)}")
    print(f"Descartadas: {len(descartadas)}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ET.ParseError, ValueError) as error:
        print(f"Error: {error}")
