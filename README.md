# TA04 - PROGRAMACIÓ I LLENGUATGES DE MARQUES
**Assignatura:** MDS / 0373 Llenguatges de Marques (Curs 2026-2027)  
**Professor:** Javier Amaya  
**Grup:** G3 (ASIXc1B - ITB Barcelona)  
**Membres de l'equip:**
- Santiago Vallejo
- Noelia Jover

---

## 📁 ESTRUCTURA DEL PROJECTE

1. **DADES I DIAGRAMES (F1 & F2):**
   - `incidencies.csv`: Registres captats mitjançant Google Forms (>4.400 incidències reals amb 10 camps).
   - `incidencies.xml`: Fitxer estructurat amb les incidències en format XML estàndard.
   - `diagrama_xml.png`: Diagrama gràfic de l'arbre XML resultant.

2. **PROCESSAMENT I ANÀLISI (F3):**
   - `analitzar_incidencies.py`: Motor d'anàlisi CLI en Python. Filtra dades invàlides (anomalies temporals, dates de l'any 2064, descripcions menors de 15 caràcters o textos buits, i registres duplicats). Mostra taules estadístiques i percentatges per terminal.

3. **PERSISTÈNCIA JSON (F4):**
   - `incidencies.json`: Emmagatzematge en format JSON. El programa comprova si el fitxer existeix i permet Sobreescriure o Afegir noves incidències evitant duplicats per ID.

4. **INTERFÍCIES D'ALTA FIDELITAT (BONUS):**
   - `interfaz_incidencies.py`: Aplicació d'escriptori completa (Tkinter) compatible amb Windows, Linux i macOS/iOS. Inclou radar telemètric, 3 temes dinàmics, visor JSON i cronòmetre per a la presentació.
   - `interfaz_web_pro.py`: Panell web local interactiu en HTML5/CSS3/JavaScript per visualitzar el radar, taules i mètriques al navegador.
   - `OBRIR_APP.bat`: Executable per iniciar ràpidament l'aplicació en Windows amb doble clic.

---

## 🚀 COM EXECUTAR EL PROJECTE

### Opció A (Consola Terminal - Rúbrica estàndard F3/F4):
```bash
python analitzar_incidencies.py incidencies.xml
```
*Per desar o actualitzar directament a JSON:*
```bash
python analitzar_incidencies.py incidencies.xml --export-json
```

### Opció B (Aplicació d'Escriptori):
Fes doble clic sobre `OBRIR_APP.bat` o executa:
```bash
python interfaz_incidencies.py
```

### Opció C (Panell Web Pro):
Executa:
```bash
python interfaz_web_pro.py
```
I s'obrirà automàticament al teu navegador web habitual.
