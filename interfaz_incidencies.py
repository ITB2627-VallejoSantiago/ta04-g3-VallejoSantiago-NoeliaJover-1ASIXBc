# -*- coding: utf-8 -*-
"""
===============================================================================
CYBER-CORE v5.0 // OBSERVATORI FORENSE D'INCIDÈNCIES [ABSOLUTE CINEMA EDITION]
Assignatura: MDS / 0373 Llenguatge de Marques - TA04
Autors: Santiago Vallejo & Noelia Jover (Grup 3) - ASIXc1B, ITB Barcelona
===============================================================================
Compatibilitat: Windows 10/11 (High-DPI), Linux (Ubuntu/Debian) i macOS/iOS.
"""

import json
import math
import os
import platform
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

# Importació del motor analític i funcions del Requisit F4
from analitzar_incidencies import (
    llegir_xml,
    validar_registres,
    calcular_estadistiques,
    exportar_json,
    CAMPS,
    ESTADISTIQUES,
)

# --- DETECCIÓ I BLINDATGE MULTIPLATAFORMA ---
SISTEMA = platform.system()

# Suport per a pantalles d'alta densitat (High-DPI / 4K / Retina)
if SISTEMA == "Windows":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

# Resolució dinàmica de fonts segons el sistema operatiu
if SISTEMA == "Windows":
    FONT_FAMILY = "Segoe UI"
    FONT_MONO = "Consolas"
elif SISTEMA == "Darwin":  # macOS / iOS
    FONT_FAMILY = "Helvetica Neue"
    FONT_MONO = "Menlo"
else:  # Linux / Unix
    FONT_FAMILY = "Ubuntu"
    FONT_MONO = "DejaVu Sans Mono"

CARPETA_BASE = Path(__file__).resolve().parent

# --- PALETES DE COLOR / TEMES CINEMATOGRÀFICS ---
TEMES = {
    "cyberpunk": {
        "nom": "🌌 Cyberpunk Neon",
        "fons": "#060913",
        "panel": "#0D1424",
        "header": "#131E35",
        "linia": "#1F2E4D",
        "text": "#F8FAFC",
        "suav": "#94A3B8",
        "primari": "#00F2FE",   # Cian elèctric
        "secundari": "#A855F7", # Violeta neó
        "accent": "#EC4899",    # Rosa neó
        "ok": "#10B981",        # Esmeralda
        "alerta": "#F43F5E",    # Vermell robí
        "avís": "#F59E0B",      # Or ambre
        "taula_sel": "#1E3A8A",
        "radar_fill": "#0369A1",
    },
    "matrix": {
        "nom": "🟢 Matrix Terminal",
        "fons": "#020B05",
        "panel": "#05160A",
        "header": "#082510",
        "linia": "#0D401C",
        "text": "#E8FBE9",
        "suav": "#72B880",
        "primari": "#00FF66",   # Fòsfor verd pur
        "secundari": "#34D399", # Menta
        "accent": "#A3E635",    # Llima
        "ok": "#22C55E",
        "alerta": "#EF4444",
        "avís": "#EAB308",
        "taula_sel": "#0F5128",
        "radar_fill": "#15803D",
    },
    "crimson": {
        "nom": "🩸 Crimson SOC",
        "fons": "#0C0709",
        "panel": "#170E12",
        "header": "#24131B",
        "linia": "#3B1B2A",
        "text": "#FFF1F2",
        "suav": "#FDA4AF",
        "primari": "#FF1E56",   # Vermell cibernètic
        "secundari": "#FB7185", # Rosa intens
        "accent": "#FFB703",    # Or defcon
        "ok": "#10B981",
        "alerta": "#FF0033",
        "avís": "#FB8500",
        "taula_sel": "#500724",
        "radar_fill": "#9F1239",
    },
}

NOMS = {
    "data": "Data i hora",
    "nom": "Nom i cognoms",
    "lloc": "Lloc de treball",
    "departament": "Departament",
    "dispositiu": "Dispositiu",
    "equip": "Equip (PC)",
    "categoria": "Categoria principal",
    "descripcio": "Descripció detallada",
    "impacte": "Estat d'operativitat",
    "abast": "Usuaris afectats",
}

COLUMNES = (
    "data", "nom", "departament", "dispositiu", "equip", "categoria", "impacte"
)


class AplicacioAbsoluteCinema(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("⚡ CYBER-CORE v5.0 // OBSERVATORI FORENSE D'INCIDÈNCIES [ASIXc1B]")
        self.geometry("1340x890")
        self.minsize(1050, 720)

        # Estat del Tema
        self.clau_tema = "cyberpunk"
        self.colors = TEMES[self.clau_tema]
        self.configure(bg=self.colors["fons"])

        # Estat de Dades
        self.registres = []
        self.acceptades = []
        self.visibles = []
        self.descartades = []
        self.ruta_actual = None
        self.cua = queue.Queue()
        self.carregant = False
        self.ordre_invers = {}
        self.tasca_cerca = None

        # Efectes de So i Animacions
        self.so_actiu = True
        self.radar_angle = 0
        self.pulsar_estat = True

        # Cronòmetre de Presentació (Requisit F5: 4 minuts exactes)
        self.temps_restant = 4 * 60  # 240 segons
        self.cronometre_actiu = False

        self.configurar_estils()
        self.crear_interficie()

        # Fil de lectura asíncrona
        self.after(100, self.recollir_resultat)

        # Animacions cícliques contínues
        self.animar_radar()
        self.animar_rellotge_i_beacon()

        # Autocàrrega intel·ligent del fitxer per defecte si existeix
        self.after(200, self.autocarregar)

    # --- SO DE ALTA TECNOLOGIA (SFX) ---
    def fer_so(self, freq=1200, dur=40):
        if not self.so_actiu or SISTEMA != "Windows":
            return
        def _beep():
            try:
                import winsound
                winsound.Beep(freq, dur)
            except Exception:
                pass
        threading.Thread(target=_beep, daemon=True).start()

    def alternar_so(self):
        self.so_actiu = not self.so_actiu
        self.btn_so.config(
            text="🔊 SO: ON" if self.so_actiu else "🔇 SO: MUT",
            fg=self.colors["primari"] if self.so_actiu else self.colors["suav"],
        )
        if self.so_actiu:
            self.fer_so(1400, 50)

    # --- GESTOR DE TEMES DINÀMICS ---
    def canviar_tema(self, nou_tema):
        if nou_tema not in TEMES:
            return
        self.fer_so(900, 30)
        self.clau_tema = nou_tema
        self.colors = TEMES[nou_tema]
        self.configure(bg=self.colors["fons"])
        self.configurar_estils()
        self.aplicar_colors_dinamics()
        self.dibuixar_grafic()
        self.dibuixar_gauge_qualitat()

    def configurar_estils(self):
        c = self.colors
        estil = ttk.Style(self)
        try:
            estil.theme_use("clam")
        except Exception:
            pass

        estil.configure(".", font=(FONT_FAMILY, 10))
        estil.configure("TFrame", background=c["fons"])
        estil.configure("TNotebook", background=c["fons"], borderwidth=0)
        estil.configure(
            "TNotebook.Tab",
            background=c["panel"],
            foreground=c["suav"],
            padding=(16, 8),
            font=(FONT_FAMILY, 9, "bold"),
            borderwidth=0,
        )
        estil.map(
            "TNotebook.Tab",
            background=[("selected", c["header"]), ("active", c["linia"])],
            foreground=[("selected", c["primari"]), ("active", c["text"])],
        )

        estil.configure(
            "Treeview",
            background=c["panel"],
            fieldbackground=c["panel"],
            foreground=c["text"],
            rowheight=30,
            font=(FONT_FAMILY, 9),
            borderwidth=0,
        )
        estil.configure(
            "Treeview.Heading",
            background=c["header"],
            foreground=c["primari"],
            padding=8,
            font=(FONT_FAMILY, 9, "bold"),
            borderwidth=1,
            relief="flat",
        )
        estil.map(
            "Treeview",
            background=[("selected", c["taula_sel"])],
            foreground=[("selected", "#FFFFFF")],
        )

        estil.configure(
            "TCombobox",
            fieldbackground=c["panel"],
            background=c["header"],
            foreground=c["text"],
            arrowcolor=c["primari"],
            padding=4,
        )

    def aplicar_colors_dinamics(self):
        c = self.colors
        self.frame_cap.config(bg=c["fons"])
        self.lbl_titol.config(fg=c["text"])
        self.lbl_subtitol.config(fg=c["suav"])
        self.barra_info.config(bg=c["fons"])
        self.lbl_fitxer.config(bg=c["fons"], fg=c["primari"])
        self.peu.config(bg=c["panel"], highlightbackground=c["linia"])
        self.lbl_estat.config(bg=c["panel"], fg=c["suav"])
        self.lbl_comptador.config(bg=c["panel"], fg=c["primari"])

        # Targetes HUD
        for k, widgets in self.hud_widgets.items():
            widgets["targeta"].config(bg=c["panel"], highlightbackground=c["linia"])
            widgets["titol"].config(bg=c["panel"], fg=c["suav"])
            widgets["num"].config(bg=c["panel"])
            widgets["sub"].config(bg=c["panel"], fg=c["suav"])

        # Filtres
        self.filtres_frame.config(bg=c["panel"], highlightbackground=c["linia"])
        self.entrada_cerca.config(bg=c["header"], fg=c["text"], insertbackground=c["primari"])

        # Canvas & Textos
        self.canvas_grafic.config(bg=c["panel"])
        self.canvas_radar.config(bg=c["header"])
        self.canvas_gauge.config(bg=c["panel"])
        self.txt_detall.config(bg=c["header"], fg=c["text"])
        self.txt_json.config(bg=c["fons"], fg=c["primari"])

    # --- CREACIÓ DE LA INTERFÍCIE MASTER ---
    def crear_interficie(self):
        c = self.colors

        # 1. COCKPIT HEADER
        self.frame_cap = tk.Frame(self, bg=c["fons"], padx=20, pady=12)
        self.frame_cap.pack(fill="x")

        # Esquerra: Títol i insígnia de seguretat
        cap_esq = tk.Frame(self.frame_cap, bg=c["fons"])
        cap_esq.pack(side="left")

        self.lbl_beacon = tk.Label(
            cap_esq,
            text="● SEC-OPS FORENSIC RADAR // ACTIVE",
            bg="#064E3B",
            fg="#34D399",
            font=(FONT_MONO, 8, "bold"),
            padx=8,
            pady=2,
        )
        self.lbl_beacon.pack(anchor="w", pady=(0, 3))

        self.lbl_titol = tk.Label(
            cap_esq,
            text="OBSERVATORI D'INCIDÈNCIES // CYBER-CORE",
            bg=c["fons"],
            fg=c["text"],
            font=(FONT_FAMILY, 19, "bold"),
        )
        self.lbl_titol.pack(anchor="w")

        self.lbl_subtitol = tk.Label(
            cap_esq,
            text="MONITORITZACIÓ, ANÀLISI FORENSE I MIGRACIÓ XML ➔ JSON • GRUP 3 (ASIXc1B)",
            bg=c["fons"],
            fg=c["suav"],
            font=(FONT_FAMILY, 8, "bold"),
        )
        self.lbl_subtitol.pack(anchor="w")

        # Dreta: Botonera Cyberpunk & Eines de Presentació
        cap_dreta = tk.Frame(self.frame_cap, bg=c["fons"])
        cap_dreta.pack(side="right", pady=4)

        # Rellotge digital en temps real
        self.lbl_rellotge = tk.Label(
            cap_dreta,
            text="--:--:--",
            bg=c["header"],
            fg=c["primari"],
            font=(FONT_MONO, 10, "bold"),
            padx=10,
            pady=4,
            relief="flat",
        )
        self.lbl_rellotge.pack(side="right", padx=(8, 0))

        # Selector de Tema
        self.tema_var = tk.StringVar(value=TEMES["cyberpunk"]["nom"])
        self.combo_tema = ttk.Combobox(
            cap_dreta,
            textvariable=self.tema_var,
            values=[t["nom"] for t in TEMES.values()],
            state="readonly",
            width=17,
        )
        self.combo_tema.pack(side="right", padx=(8, 0))
        self.combo_tema.bind("<<ComboboxSelected>>", self.on_seleccio_tema)

        # Botó So (SFX)
        self.btn_so = tk.Button(
            cap_dreta,
            text="🔊 SO: ON",
            bg=c["header"],
            fg=c["primari"],
            font=(FONT_FAMILY, 8, "bold"),
            padx=8,
            pady=3,
            relief="flat",
            activebackground=c["linia"],
            activeforeground="#FFFFFF",
            command=self.alternar_so,
        )
        self.btn_so.pack(side="right", padx=(8, 0))

        # Botó Presentació
        self.btn_presentacio = tk.Button(
            cap_dreta,
            text="⏱️ CRONÒMETRE (4m)",
            bg="#312E81",
            fg="#A5B4FC",
            font=(FONT_FAMILY, 8, "bold"),
            padx=8,
            pady=3,
            relief="flat",
            activebackground="#4338CA",
            activeforeground="#FFFFFF",
            command=self.anar_pestanya_presentacio,
        )
        self.btn_presentacio.pack(side="right", padx=(8, 0))

        # Botó Web Pro
        btn_web = tk.Button(
            cap_dreta,
            text="🌐 PANELL WEB PRO",
            bg="#1E293B",
            fg=c["text"],
            font=(FONT_FAMILY, 8, "bold"),
            padx=9,
            pady=3,
            relief="flat",
            activebackground="#334155",
            activeforeground="#FFFFFF",
            command=self.obrir_panell_web,
        )
        btn_web.pack(side="right", padx=(8, 0))

        # Botó Exportar JSON (F4)
        btn_json = tk.Button(
            cap_dreta,
            text="💾 EXPORTAR JSON (F4)",
            bg="#2563EB",
            fg="#FFFFFF",
            font=(FONT_FAMILY, 8, "bold"),
            padx=10,
            pady=3,
            relief="flat",
            activebackground="#1D4ED8",
            activeforeground="#FFFFFF",
            command=self.obrir_dialeg_json,
        )
        btn_json.pack(side="right", padx=(8, 0))

        # Botó Obrir XML
        self.btn_obrir = tk.Button(
            cap_dreta,
            text="📂 OBRIR XML",
            bg="#0284C7",
            fg="#FFFFFF",
            font=(FONT_FAMILY, 8, "bold"),
            padx=10,
            pady=3,
            relief="flat",
            activebackground="#0369A1",
            activeforeground="#FFFFFF",
            command=self.obrir_xml,
        )
        self.btn_obrir.pack(side="right", padx=(8, 0))

        # 2. STATUS & FILE PATH BANNER
        self.barra_info = tk.Frame(self, bg=c["fons"], padx=20, pady=0)
        self.barra_info.pack(fill="x")

        self.lbl_fitxer = tk.Label(
            self.barra_info,
            text="⚡ SISTEMA PREPARAT // Esperant fitxer XML...",
            bg=c["fons"],
            fg=c["primari"],
            font=(FONT_MONO, 9),
            anchor="w",
        )
        self.lbl_fitxer.pack(side="left")

        self.ordre_data = tk.StringVar(value="Mes/dia/any")
        sel_ordre = ttk.Combobox(
            self.barra_info,
            textvariable=self.ordre_data,
            values=["Mes/dia/any", "Dia/mes/any"],
            state="readonly",
            width=12,
        )
        sel_ordre.pack(side="right")
        sel_ordre.bind("<<ComboboxSelected>>", lambda e: self.reprocessar_ordre())
        tk.Label(self.barra_info, text="Ordre dates:", bg=c["fons"], fg=c["suav"], font=(FONT_FAMILY, 8)).pack(side="right", padx=(0, 6))

        # 3. HUD DE TELEMETRIA CINEMATOGRÀFICA (RADAR + TARGETES NEÓ + GAUGE)
        self.hud_frame = tk.Frame(self, bg=c["fons"], padx=20, pady=10)
        self.hud_frame.pack(fill="x")

        # Widget 1: Radar circular animat
        self.radar_box = tk.Frame(self.hud_frame, bg=c["panel"], highlightbackground=c["linia"], highlightthickness=1, padx=6, pady=4)
        self.radar_box.pack(side="left", padx=(0, 10))

        tk.Label(self.radar_box, text="RADAR TELEMÈTRIC", bg=c["panel"], fg=c["suav"], font=(FONT_MONO, 7, "bold")).pack(anchor="w")
        self.canvas_radar = tk.Canvas(self.radar_box, width=72, height=72, bg=c["header"], highlightthickness=0)
        self.canvas_radar.pack(pady=2)

        # Widget 2: Les 4 Targetes de Mètriques
        self.targetes_resum = tk.Frame(self.hud_frame, bg=c["fons"])
        self.targetes_resum.pack(side="left", fill="x", expand=True)

        self.hud_widgets = {}
        metriques = [
            ("LLEGIDES", "Total XML", c["secundari"]),
            ("ACCEPTADES", "Nominals i Válides", c["ok"]),
            ("DESCARTADES", "Anomalies / Brossa", c["alerta"]),
            ("QUALITAT", "Ràtio d'Integritat", c["primari"]),
        ]

        for idx, (nom, subtext, color_num) in enumerate(metriques):
            self.targetes_resum.columnconfigure(idx, weight=1)
            targeta = tk.Frame(self.targetes_resum, bg=c["panel"], highlightbackground=c["linia"], highlightthickness=1, padx=12, pady=8)
            targeta.grid(row=0, column=idx, sticky="ew", padx=(0, 8 if idx < 3 else 0))

            lbl_titol = tk.Label(targeta, text=nom, bg=c["panel"], fg=c["suav"], font=(FONT_FAMILY, 8, "bold"))
            lbl_titol.pack(anchor="w")

            var_num = tk.StringVar(value="—")
            lbl_num = tk.Label(targeta, textvariable=var_num, bg=c["panel"], fg=color_num, font=(FONT_FAMILY, 19, "bold"))
            lbl_num.pack(anchor="w")

            lbl_sub = tk.Label(targeta, text=subtext, bg=c["panel"], fg=c["suav"], font=(FONT_FAMILY, 7))
            lbl_sub.pack(anchor="w")

            self.hud_widgets[nom] = {
                "targeta": targeta,
                "titol": lbl_titol,
                "num": lbl_num,
                "sub": lbl_sub,
                "var": var_num,
            }

        # Widget 3: Gauge semicircular de qualitat forense
        self.gauge_box = tk.Frame(self.hud_frame, bg=c["panel"], highlightbackground=c["linia"], highlightthickness=1, padx=10, pady=4)
        self.gauge_box.pack(side="right", padx=(10, 0))

        tk.Label(self.gauge_box, text="INTEGRITAT DE DADES", bg=c["panel"], fg=c["suav"], font=(FONT_MONO, 7, "bold")).pack(anchor="w")
        self.canvas_gauge = tk.Canvas(self.gauge_box, width=120, height=52, bg=c["panel"], highlightthickness=0)
        self.canvas_gauge.pack(pady=(2, 0))
        self.lbl_gauge_text = tk.Label(self.gauge_box, text="0.0% OPTIMAL", bg=c["panel"], fg=c["primari"], font=(FONT_FAMILY, 7, "bold"))
        self.lbl_gauge_text.pack(anchor="center")

        # 4. BARRA DE FILTRES I CERCA GLOBAL
        self.filtres_frame = tk.Frame(self, bg=c["panel"], highlightbackground=c["linia"], highlightthickness=1, padx=16, pady=10)
        self.filtres_frame.pack(fill="x", padx=20, pady=(0, 10))
        self.filtres_frame.columnconfigure(0, weight=2)

        tk.Label(self.filtres_frame, text="🔍 Cerca intel·ligent (Nom, PC, Departament, Problema):", bg=c["panel"], fg=c["suav"], font=(FONT_FAMILY, 8, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.cerca = tk.StringVar()
        self.entrada_cerca = tk.Entry(self.filtres_frame, textvariable=self.cerca, bg=c["header"], fg=c["text"], insertbackground=c["primari"], relief="flat", font=(FONT_FAMILY, 10))
        self.entrada_cerca.grid(row=1, column=0, sticky="ew", padx=(0, 10), ipady=4)
        self.cerca.trace_add("write", self.programar_cerca)

        self.filtres_combos = {}
        camps_filtre = [
            ("departament", "Departament"),
            ("categoria", "Categoria"),
            ("dispositiu", "Dispositiu"),
            ("impacte", "Impacte"),
        ]

        for col_idx, (camp, etiqueta) in enumerate(camps_filtre, start=1):
            self.filtres_frame.columnconfigure(col_idx, weight=1)
            tk.Label(self.filtres_frame, text=etiqueta, bg=c["panel"], fg=c["suav"], font=(FONT_FAMILY, 8, "bold")).grid(row=0, column=col_idx, sticky="w", pady=(0, 4))
            combo = ttk.Combobox(self.filtres_frame, state="readonly", values=["Tots"])
            combo.current(0)
            combo.grid(row=1, column=col_idx, sticky="ew", padx=(0, 8 if col_idx < 4 else 10))
            combo.bind("<<ComboboxSelected>>", lambda e: self.aplicar_filtres())
            self.filtres_combos[camp] = combo

        btn_netejar = tk.Button(
            self.filtres_frame,
            text="✕ Netejar",
            bg=c["header"],
            fg=c["text"],
            font=(FONT_FAMILY, 8, "bold"),
            padx=10,
            pady=4,
            relief="flat",
            command=self.netejar_filtres,
        )
        btn_netejar.grid(row=1, column=5, sticky="e")

        # 5. WORKSPACE AMB PESTANYES
        self.pestanyes = ttk.Notebook(self)
        self.pestanyes.pack(fill="both", expand=True, padx=20, pady=(0, 8))

        self.crear_pestanya_radar()
        self.crear_pestanya_telemetria()
        self.crear_pestanya_forense()
        self.crear_pestanya_json()
        self.crear_pestanya_presentacio()
        self.crear_pestanya_teoria()

        # 6. FOOTER / STATUS BAR
        self.peu = tk.Frame(self, bg=c["panel"], padx=16, pady=5, highlightbackground=c["linia"], highlightthickness=1)
        self.peu.pack(fill="x", side="bottom")

        self.lbl_estat = tk.Label(
            self.peu, text="⚡ CYBER-CORE NOMINAL // Tots els sistemes operatius preparats", bg=c["panel"], fg=c["suav"], font=(FONT_MONO, 8)
        )
        self.lbl_estat.pack(side="left")

        self.lbl_comptador = tk.Label(
            self.peu, text="Mostrant 0 incidències", bg=c["panel"], fg=c["primari"], font=(FONT_FAMILY, 8, "bold")
        )
        self.lbl_comptador.pack(side="right")

    # --- PESTANYA 1: RADAR D'INCIDÈNCIES & FITXA FORENSE ---
    def crear_pestanya_radar(self):
        c = self.colors
        pestanya = ttk.Frame(self.pestanyes, padding=8)
        self.pestanyes.add(pestanya, text="🛰️ Radar d'Incidències")

        divisor = ttk.Panedwindow(pestanya, orient="vertical")
        divisor.pack(fill="both", expand=True)

        marc_taula = ttk.Frame(divisor)
        divisor.add(marc_taula, weight=3)

        self.taula = ttk.Treeview(marc_taula, columns=COLUMNES, show="headings")
        sb_y = ttk.Scrollbar(marc_taula, orient="vertical", command=self.taula.yview)
        sb_x = ttk.Scrollbar(marc_taula, orient="horizontal", command=self.taula.xview)
        self.taula.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)

        self.taula.grid(row=0, column=0, sticky="nsew")
        sb_y.grid(row=0, column=1, sticky="ns")
        sb_x.grid(row=1, column=0, sticky="ew")
        marc_taula.rowconfigure(0, weight=1)
        marc_taula.columnconfigure(0, weight=1)

        titols = [NOMS[c_nom] for c_nom in COLUMNES]
        amplades = [135, 160, 175, 130, 95, 210, 180]

        for camp, titol, amplada in zip(COLUMNES, titols, amplades):
            self.taula.heading(camp, text=titol, command=lambda c_col=camp: self.ordenar(c_col))
            self.taula.column(camp, width=amplada, minwidth=80)

        self.taula.bind("<<TreeviewSelect>>", self.mostrar_detall_incidencia)

        # Fitxa forense inferior
        marc_detall = tk.Frame(divisor, bg=c["panel"], highlightbackground=c["linia"], highlightthickness=1, padx=12, pady=8)
        divisor.add(marc_detall, weight=2)

        tk.Label(
            marc_detall, text="📋 DOSSIER FORENSE D'INVESTIGACIÓ DE LA INCIDÈNCIA", bg=c["panel"], fg=c["primari"], font=(FONT_FAMILY, 9, "bold")
        ).pack(anchor="w", pady=(0, 4))

        self.txt_detall = tk.Text(
            marc_detall,
            bg=c["header"],
            fg=c["text"],
            wrap="word",
            font=(FONT_MONO, 9),
            relief="flat",
            padx=12,
            pady=8,
            height=6,
        )
        sb_detall = ttk.Scrollbar(marc_detall, command=self.txt_detall.yview)
        self.txt_detall.configure(yscrollcommand=sb_detall.set)
        sb_detall.pack(side="right", fill="y")
        self.txt_detall.pack(side="left", fill="both", expand=True)

        self.escriure_detall("Selecciona qualsevol incidència a la graella per examinar la seva fitxa tècnica completa.")

    # --- PESTANYA 2: TELEMETRIA & GRÀFICS DINÀMICS ---
    def crear_pestanya_telemetria(self):
        c = self.colors
        pestanya = ttk.Frame(self.pestanyes, padding=10)
        self.pestanyes.add(pestanya, text="📊 Telemetria & Gràfics")

        barra_ctrl = tk.Frame(pestanya, bg=c["panel"], padx=12, pady=8, highlightbackground=c["linia"], highlightthickness=1)
        barra_ctrl.pack(fill="x", pady=(0, 8))

        tk.Label(barra_ctrl, text="DISTRIBUCIÓ TELEMÈTRICA:", bg=c["panel"], fg=c["suav"], font=(FONT_FAMILY, 9, "bold")).pack(side="left", padx=(0, 10))

        self.camp_grafic = tk.StringVar(value="categoria")

        for camp in ESTADISTIQUES:
            btn = tk.Button(
                barra_ctrl,
                text=NOMS[camp],
                bg=c["header"],
                fg=c["text"],
                font=(FONT_FAMILY, 8, "bold"),
                padx=9,
                pady=4,
                relief="flat",
                command=lambda c_val=camp: self.canviar_grafic(c_val),
            )
            btn.pack(side="left", padx=3)

        self.banner_insight = tk.Label(
            pestanya,
            text="Carregant telemetria...",
            bg=c["header"],
            fg=c["primari"],
            font=(FONT_FAMILY, 9, "bold"),
            padx=12,
            pady=6,
        )
        self.banner_insight.pack(fill="x", pady=(0, 8))

        contenidor = tk.Frame(pestanya, bg=c["panel"], highlightbackground=c["linia"], highlightthickness=1)
        contenidor.pack(fill="both", expand=True)

        self.canvas_grafic = tk.Canvas(contenidor, bg=c["panel"], highlightthickness=0)
        sb_c = ttk.Scrollbar(contenidor, orient="vertical", command=self.canvas_grafic.yview)
        self.canvas_grafic.configure(yscrollcommand=sb_c.set)
        sb_c.pack(side="right", fill="y")
        self.canvas_grafic.pack(side="left", fill="both", expand=True)
        self.canvas_grafic.bind("<Configure>", lambda e: self.dibuixar_grafic())

    # --- PESTANYA 3: FILTRE FORENSE (DESCARTADES & 2064) ---
    def crear_pestanya_forense(self):
        c = self.colors
        pestanya = ttk.Frame(self.pestanyes, padding=10)
        self.pestanyes.add(pestanya, text="☣️ Filtre Forense & Anomalies")

        cap = tk.Frame(pestanya, bg=c["panel"], padx=14, pady=10, highlightbackground=c["linia"], highlightthickness=1)
        cap.pack(fill="x", pady=(0, 8))

        tk.Label(
            cap,
            text="DEPURACIÓ FORENSE DE REGISTRES CORRUPTES, DUPLICATS O DATES FUTURES (Ex: any 2064)",
            bg=c["panel"],
            fg=c["alerta"],
            font=(FONT_FAMILY, 10, "bold"),
        ).pack(anchor="w")

        tk.Label(
            cap,
            text="Tots els registres aïllats en aquesta llista no contaminen les estadístiques ni s'exportaran a producció.",
            bg=c["panel"],
            fg=c["suav"],
            font=(FONT_FAMILY, 8),
        ).pack(anchor="w", pady=(2, 0))

        marc_t = ttk.Frame(pestanya)
        marc_t.pack(fill="both", expand=True)

        self.taula_descartades = ttk.Treeview(marc_t, columns=("posicio", "motius"), show="headings")
        sb_y = ttk.Scrollbar(marc_t, orient="vertical", command=self.taula_descartades.yview)
        self.taula_descartades.configure(yscrollcommand=sb_y.set)

        self.taula_descartades.heading("posicio", text="Registre XML #")
        self.taula_descartades.heading("motius", text="Infracció de qualitat detectada")
        self.taula_descartades.column("posicio", width=120, stretch=False)
        self.taula_descartades.column("motius", width=850)

        self.taula_descartades.pack(side="left", fill="both", expand=True)
        sb_y.pack(side="right", fill="y")
        self.taula_descartades.bind("<<TreeviewSelect>>", self.detall_descartada)

    # --- PESTANYA 4: GESTOR JSON (REQUISIT F4) ---
    def crear_pestanya_json(self):
        c = self.colors
        pestanya = ttk.Frame(self.pestanyes, padding=12)
        self.pestanyes.add(pestanya, text="💾 Gestor JSON (F4)")

        caixa_ctrl = tk.Frame(pestanya, bg=c["panel"], padx=14, pady=12, highlightbackground=c["linia"], highlightthickness=1)
        caixa_ctrl.pack(fill="x", pady=(0, 10))

        tk.Label(
            caixa_ctrl,
            text="REQUISIT F4: MIGRACIÓ I PERSISTÈNCIA EN JSON (incidencies.json)",
            bg=c["panel"],
            fg=c["primari"],
            font=(FONT_FAMILY, 11, "bold"),
        ).pack(anchor="w")

        tk.Label(
            caixa_ctrl,
            text="Comprova si el fitxer ja existeix: permet Sobreescriure completament o Afegir noves incidències sense duplicar per ID.",
            bg=c["panel"],
            fg=c["suav"],
            font=(FONT_FAMILY, 8),
        ).pack(anchor="w", pady=(2, 10))

        fila_btn = tk.Frame(caixa_ctrl, bg=c["panel"])
        fila_btn.pack(anchor="w")

        tk.Button(
            fila_btn,
            text="⚡ Sobreescriure incidencies.json",
            bg=c["header"],
            fg=c["text"],
            font=(FONT_FAMILY, 8, "bold"),
            padx=10,
            pady=4,
            relief="flat",
            command=lambda: self.executar_exportacio_json(mode="overwrite"),
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            fila_btn,
            text="➕ Afegir Noves (Sense Duplicats per ID)",
            bg="#2563EB",
            fg="#FFFFFF",
            font=(FONT_FAMILY, 8, "bold"),
            padx=10,
            pady=4,
            relief="flat",
            command=lambda: self.executar_exportacio_json(mode="append"),
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            fila_btn,
            text="📋 Copiar al Portapapers",
            bg=c["header"],
            fg=c["primari"],
            font=(FONT_FAMILY, 8, "bold"),
            padx=10,
            pady=4,
            relief="flat",
            command=self.copiar_json_clipboard,
        ).pack(side="left")

        self.lbl_estat_json = tk.Label(
            caixa_ctrl,
            text="Fitxer JSON: Comprovant...",
            bg=c["panel"],
            fg=c["avís"],
            font=(FONT_MONO, 8),
        )
        self.lbl_estat_json.pack(anchor="w", pady=(8, 0))

        # Visor de codi JSON
        marc_visor = tk.Frame(pestanya, bg=c["fons"], highlightbackground=c["linia"], highlightthickness=1)
        marc_visor.pack(fill="both", expand=True)

        self.txt_json = tk.Text(
            marc_visor,
            bg=c["fons"],
            fg=c["primari"],
            wrap="none",
            font=(FONT_MONO, 9),
            relief="flat",
            padx=12,
            pady=8,
        )
        sb_y = ttk.Scrollbar(marc_visor, orient="vertical", command=self.txt_json.yview)
        sb_x = ttk.Scrollbar(marc_visor, orient="horizontal", command=self.txt_json.xview)
        self.txt_json.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)

        self.txt_json.grid(row=0, column=0, sticky="nsew")
        sb_y.grid(row=0, column=1, sticky="ns")
        sb_x.grid(row=1, column=0, sticky="ew")
        marc_visor.rowconfigure(0, weight=1)
        marc_visor.columnconfigure(0, weight=1)

    # --- PESTANYA 5: COCKPIT DE PRESENTACIÓ (F5 - 4 MINUTS & 3 IDIOMES) ---
    def crear_pestanya_presentacio(self):
        c = self.colors
        pestanya = ttk.Frame(self.pestanyes, padding=14)
        self.pestanyes.add(pestanya, text="⏱️ Cronòmetre")

        targeta = tk.Frame(pestanya, bg=c["panel"], padx=24, pady=24, highlightbackground=c["linia"], highlightthickness=1)
        targeta.pack(fill="both", expand=True)

        tk.Label(
            targeta,
            text="⏱️ CRONÒMETRE DE CONTROL DE TEMPS",
            bg=c["panel"],
            fg=c["primari"],
            font=(FONT_FAMILY, 15, "bold"),
        ).pack(anchor="w", pady=(0, 6))

        tk.Label(
            targeta,
            text="Temporitzador de compte enrere per a la presentació del projecte.",
            bg=c["panel"],
            fg=c["suav"],
            font=(FONT_FAMILY, 9),
        ).pack(anchor="w", pady=(0, 20))

        # Rellotge de compte enrere gegant
        caixa_timer = tk.Frame(targeta, bg=c["header"], padx=24, pady=20, highlightbackground=c["linia"], highlightthickness=1)
        caixa_timer.pack(fill="x", pady=(0, 14))

        self.lbl_compte_enrere = tk.Label(
            caixa_timer,
            text="04:00",
            bg=c["header"],
            fg=c["ok"],
            font=(FONT_MONO, 52, "bold"),
        )
        self.lbl_compte_enrere.pack(side="left", padx=(10, 25))

        fila_timer_btn = tk.Frame(caixa_timer, bg=c["header"])
        fila_timer_btn.pack(side="left")

        self.btn_iniciar_timer = tk.Button(
            fila_timer_btn,
            text="▶ INICIAR CRONÒMETRE",
            bg="#16A34A",
            fg="#FFFFFF",
            font=(FONT_FAMILY, 11, "bold"),
            padx=16,
            pady=8,
            relief="flat",
            command=self.iniciar_aturar_timer,
        )
        self.btn_iniciar_timer.pack(side="left", padx=(0, 10))

        tk.Button(
            fila_timer_btn,
            text="🔄 REINICIAR (04:00)",
            bg=c["panel"],
            fg=c["text"],
            font=(FONT_FAMILY, 10, "bold"),
            padx=14,
            pady=8,
            relief="flat",
            command=self.reiniciar_timer,
        ).pack(side="left")


    # --- PESTANYA 6: TEORIA (DADES VS INFORMACIÓ) ---
    def crear_pestanya_teoria(self):
        c = self.colors
        pestanya = ttk.Frame(self.pestanyes, padding=14)
        self.pestanyes.add(pestanya, text="🧠 Teoria: Dades vs Info")

        targeta = tk.Frame(pestanya, bg=c["panel"], padx=18, pady=14, highlightbackground=c["linia"], highlightthickness=1)
        targeta.pack(fill="both", expand=True)

        tk.Label(
            targeta,
            text="FONAMENTS TEÒRICS DE GESTIÓ DE LA INFORMACIÓ I RGPD (RÚBRICA F3)",
            bg=c["panel"],
            fg=c["primari"],
            font=(FONT_FAMILY, 11, "bold"),
        ).pack(anchor="w", pady=(0, 8))

        teoria_text = (
            "1. QUINA ÉS LA DIFERÈNCIA EXACTA ENTRE DADES I INFORMACIÓ?\n"
            "──────────────────────────────────────────────────────────────────────────────\n"
            "• DADA (DATA): És un símbol o valor cru sense context, relació ni interpretació.\n"
            "  Exemples del nostre fitxer: 'PC-67', '2026-11-03', 'Perifèrics', '4407'.\n"
            "  Per si sola, una dada no té capacitat de reduir la incertesa ni permet prendre decisions.\n\n"
            "• INFORMACIÓ (INFORMATION): Són dades processades, netejades, agrupades i dotades de significat.\n"
            "  Exemple a la nostra organització: 'Dels 4.054 incidents vàlids, el 58.8% afecten portàtils,\n"
            "  mentre que la causa principal són fallades de perifèrics (26.3%) causant un 65.3% de bloqueig parcial.'\n"
            "  La informació aporta valor estratègic per a la gestió IT i el compliment de seguretat (GRC).\n\n"
            "2. EL PERQUÈ DEL FILTRATGE DE REGISTRES ERRONIS O INVÀLIDS:\n"
            "──────────────────────────────────────────────────────────────────────────────\n"
            "En ciberseguretat regeix el principi GIGO ('Garbage In, Garbage Out'). Si s'inclouen registres\n"
            "amb dates de l'any 2064, descripcions buides o registres duplicats (69 detectats al nostre XML),\n"
            "les mètriques de rendiment i auditories queden completament desvirtuades.\n\n"
            "3. PRIVACITAT I RGPD RESPECTE A L'ÚS D'INTEL·LIGÈNCIA ARTIFICIAL:\n"
            "──────────────────────────────────────────────────────────────────────────────\n"
            "El Reglament General de Protecció de Dades (RGPD / GDPR) prohibeix la cessió de dades personals\n"
            "d'usuaris (noms, correus, identificadors d'equips) a models d'IA comercials externs sense garanties\n"
            "ni consentiment exprés. Per aquesta raó, tot el processament s'executa 100% en local amb Python."
        )

        txt_t = tk.Text(targeta, bg=c["header"], fg=c["text"], font=(FONT_MONO, 10), relief="flat", padx=12, pady=10)
        txt_t.insert("1.0", teoria_text)
        txt_t.configure(state="disabled")
        txt_t.pack(fill="both", expand=True)

    # --- CONTROL DEL CRONÒMETRE F5 ---
    def anar_pestanya_presentacio(self):
        self.fer_so(1200, 40)
        self.pestanyes.select(4)

    def iniciar_aturar_timer(self):
        self.cronometre_actiu = not self.cronometre_actiu
        if self.cronometre_actiu:
            self.fer_so(1500, 50)
            self.btn_iniciar_timer.config(text="⏸ PAUSAR CRONÒMETRE", bg="#D97706")
            self.executar_tick_timer()
        else:
            self.fer_so(800, 50)
            self.btn_iniciar_timer.config(text="▶ REPRENDRE", bg="#16A34A")

    def reiniciar_timer(self):
        self.cronometre_actiu = False
        self.temps_restant = 4 * 60
        self.btn_iniciar_timer.config(text="▶ INICIAR CRONÒMETRE", bg="#16A34A")
        self.lbl_compte_enrere.config(text="04:00", fg=self.colors["ok"])

    def executar_tick_timer(self):
        if not self.cronometre_actiu:
            return

        if self.temps_restant > 0:
            self.temps_restant -= 1
            minuts = self.temps_restant // 60
            segons = self.temps_restant % 60
            self.lbl_compte_enrere.config(text=f"{minuts:02d}:{segons:02d}")

            # Canvi de color segons el temps restant
            if self.temps_restant <= 30:
                self.lbl_compte_enrere.config(fg=self.colors["alerta"])
                if self.temps_restant % 5 == 0:
                    self.fer_so(2000, 60)
            elif self.temps_restant <= 60:
                self.lbl_compte_enrere.config(fg=self.colors["avís"])

            self.after(1000, self.executar_tick_timer)
        else:
            self.cronometre_actiu = False
            self.lbl_compte_enrere.config(text="TEMPS ESGOTAT!", fg=self.colors["alerta"])
            self.fer_so(700, 300)

    # --- ANIMACIÓ DEL RADAR I RELOGE ---
    def animar_radar(self):
        c = self.colors
        can = self.canvas_radar
        can.delete("all")

        cx, cy, r = 36, 36, 32
        can.create_oval(cx - r, cy - r, cx + r, cy + r, outline=c["linia"], width=1)
        can.create_oval(cx - r*0.66, cy - r*0.66, cx + r*0.66, cy + r*0.66, outline=c["linia"], width=1)
        can.create_oval(cx - r*0.33, cy - r*0.33, cx + r*0.33, cy + r*0.33, outline=c["linia"], width=1)
        can.create_line(cx - r, cy, cx + r, cy, fill=c["linia"])
        can.create_line(cx, cy - r, cx, cy + r, fill=c["linia"])

        # Línia d'escombrat giratòria
        rad = math.radians(self.radar_angle)
        ex = cx + r * math.cos(rad)
        ey = cy + r * math.sin(rad)
        can.create_line(cx, cy, ex, ey, fill=c["primari"], width=2)

        # Punts de detecció (Blips de la xarxa)
        if len(self.acceptades) > 0:
            for p_rad, dist in [(45, 0.5), (130, 0.75), (250, 0.35), (310, 0.8)]:
                bx = cx + r * dist * math.cos(math.radians(p_rad))
                by = cy + r * dist * math.sin(math.radians(p_rad))
                can.create_oval(bx - 2, by - 2, bx + 2, by + 2, fill=c["ok"], outline="")

        self.radar_angle = (self.radar_angle + 6) % 360
        self.after(50, self.animar_radar)

    def animar_rellotge_i_beacon(self):
        ara = datetime.now().strftime("%H:%M:%S")
        self.lbl_rellotge.config(text=ara)

        self.pulsar_estat = not self.pulsar_estat
        c_beacon_fg = "#34D399" if self.pulsar_estat else "#10B981"
        self.lbl_beacon.config(fg=c_beacon_fg)

        self.after(700, self.animar_rellotge_i_beacon)

    def dibuixar_gauge_qualitat(self):
        c = self.colors
        can = self.canvas_gauge
        can.delete("all")

        total = len(self.registres)
        valid = len(self.acceptades)
        pct = (valid / total * 100) if total else 0.0

        cx, cy, r = 60, 48, 42
        # Arc de fons
        can.create_arc(cx - r, cy - r, cx + r, cy + r, start=0, extent=180, style="arc", outline=c["linia"], width=8)

        # Arc de percentatge neó
        if pct > 0:
            extent = min(180, max(0, 180 * (pct / 100)))
            can.create_arc(cx - r, cy - r, cx + r, cy + r, start=180, extent=-extent, style="arc", outline=c["ok"], width=8)

        self.lbl_gauge_text.config(text=f"{pct:.1f}% OPTIMAL", fg=c["ok"] if pct >= 85 else c["avís"])

    # --- CÀRREGA I PROCESSAMENT DE DADES ---
    def autocarregar(self):
        fitxer = CARPETA_BASE / "incidencies.xml"
        if not fitxer.exists():
            fitxer = CARPETA_BASE / "incidencies_filtrades.xml"
        if fitxer.exists():
            self.carregar_fitxer(fitxer)

    def obrir_xml(self):
        if self.carregant:
            return
        self.fer_so(1100, 30)

        ruta = filedialog.askopenfilename(
            title="Selecciona fitxer XML d'incidències",
            initialdir=CARPETA_BASE,
            filetypes=[("Documents XML", "*.xml"), ("Tots els fitxers", "*.*")],
        )
        if ruta:
            self.carregar_fitxer(Path(ruta))

    def carregar_fitxer(self, ruta_fitxer):
        ordre = "mdy" if self.ordre_data.get() == "Mes/dia/any" else "dmy"
        self.carregant = True
        self.btn_obrir.config(state="disabled")
        self.lbl_fitxer.config(text=f"🔄 Processant i verificant: {ruta_fitxer.name}...", fg=self.colors["avís"])
        self.lbl_estat.config(text="Executant algoritme forense de detecció d'anomalies...")

        threading.Thread(
            target=self.tasca_lectura, args=(ruta_fitxer, ordre), daemon=True
        ).start()

    def tasca_lectura(self, ruta, ordre):
        try:
            regs = llegir_xml(ruta)
            acc, desc = validar_registres(regs, ordre)
            self.cua.put(("ok", str(ruta), regs, acc, desc))
        except Exception as e:
            self.cua.put(("error", str(e)))

    def recollir_resultat(self):
        try:
            res = self.cua.get_nowait()
        except queue.Empty:
            pass
        else:
            self.carregant = False
            self.btn_obrir.config(state="normal")

            if res[0] == "error":
                self.fer_so(400, 150)
                self.lbl_fitxer.config(text="❌ Error de lectura XML", fg=self.colors["alerta"])
                messagebox.showerror("Error de lectura XML", res[1])
            else:
                self.fer_so(1500, 40)
                _, ruta, self.registres, self.acceptades, self.descartades = res
                self.ruta_actual = ruta
                p_ruta = Path(ruta)

                total = len(self.registres)
                n_acc = len(self.acceptades)
                n_desc = len(self.descartades)
                qualitat = (n_acc / total * 100) if total else 0

                self.lbl_fitxer.config(
                    text=f"✔ Fitxer actiu: {p_ruta.name} ({total:,} registres totals) — {p_ruta.resolve()}",
                    fg=self.colors["primari"],
                )

                # Actualitzar targetes HUD
                self.hud_widgets["LLEGIDES"]["var"].set(f"{total:,}")
                self.hud_widgets["ACCEPTADES"]["var"].set(f"{n_acc:,}")
                self.hud_widgets["DESCARTADES"]["var"].set(f"{n_desc:,}")
                self.hud_widgets["QUALITAT"]["var"].set(f"{qualitat:.1f}%")

                self.dibuixar_gauge_qualitat()

                # Actualitzar desplegables
                for camp, combo in self.filtres_combos.items():
                    valors = sorted({
                        fila[camp] for fila in self.acceptades if fila.get(camp)
                    }, key=str.casefold)
                    combo.configure(values=["Tots"] + valors)

                # Omplir taula descartades
                self.taula_descartades.delete(*self.taula_descartades.get_children())
                for idx, (pos, motius) in enumerate(self.descartades):
                    self.taula_descartades.insert(
                        "", "end", iid=str(idx), values=(f"#{pos}", "; ".join(motius))
                    )

                self.netejar_filtres()
                self.lbl_estat.config(text=f"✔ Dades netejades amb èxit • {n_acc:,} registres llestos per a l'anàlisi.")
                self.mostrar_preview_json()

        self.after(100, self.recollir_resultat)

    def reprocessar_ordre(self):
        if self.ruta_actual and not self.carregant:
            self.carregar_fitxer(Path(self.ruta_actual))

    def on_seleccio_tema(self, _=None):
        nom_triat = self.tema_var.get()
        for k, v in TEMES.items():
            if v["nom"] == nom_triat:
                self.canviar_tema(k)
                break

    # --- FILTRES I CERCA ---
    def programar_cerca(self, *_):
        if self.tasca_cerca is not None:
            self.after_cancel(self.tasca_cerca)
        self.tasca_cerca = self.after(180, self.aplicar_filtres)

    def netejar_filtres(self):
        self.cerca.set("")
        for combo in self.filtres_combos.values():
            combo.current(0)
        self.aplicar_filtres()

    def aplicar_filtres(self):
        if self.tasca_cerca is not None:
            self.after_cancel(self.tasca_cerca)
            self.tasca_cerca = None

        terme = self.cerca.get().strip().casefold()
        self.visibles = []

        for fila in self.acceptades:
            if terme and not any(terme in str(v).casefold() for v in fila.values()):
                continue

            coincideix = True
            for camp, combo in self.filtres_combos.items():
                if combo.current() > 0 and fila.get(camp) != combo.get():
                    coincideix = False
                    break
            if not coincideix:
                continue

            self.visibles.append(fila)

        self.actualitzar_taula()
        self.lbl_comptador.config(text=f"Mostrant {len(self.visibles):,} de {len(self.acceptades):,} acceptades")
        self.dibuixar_grafic()

    def actualitzar_taula(self):
        self.taula.delete(*self.taula.get_children())
        for idx, fila in enumerate(self.visibles):
            valors = [fila.get(c, "—") or "—" for c in COLUMNES]
            self.taula.insert("", "end", iid=str(idx), values=valors)

    def ordenar(self, camp):
        self.fer_so(1000, 25)
        invers = self.ordre_invers.get(camp, False)
        self.visibles.sort(key=lambda r: str(r.get(camp, "")).casefold(), reverse=invers)
        self.ordre_invers[camp] = not invers
        self.actualitzar_taula()
        self.lbl_estat.config(text=f"Graella reordenada per '{NOMS[camp]}' ({'descendent' if invers else 'ascendent'}).")

    def mostrar_detall_incidencia(self, _=None):
        sel = self.taula.selection()
        if not sel:
            return
        self.fer_so(1300, 20)
        fila = self.visibles[int(sel[0])]

        impacte = fila.get("impacte", "")
        indicador = "🔴 BLOQUEIG TOTAL" if "total" in impacte.lower() else ("🟠 BLOQUEIG PARCIAL" if "parcial" in impacte.lower() else "🟢 OPERATIU")

        dossier = (
            f"IDENTIFICADOR FORENSE // EQUIP: {fila.get('equip', 'N/A')}  |  ESTAT D'OPERATIVITAT: {indicador}\n"
            f"────────────────────────────────────────────────────────────────────────────────────────────\n"
            f"• DATA I HORA REGISTRE  : {fila.get('data', '—')}\n"
            f"• USUARI AFECTAT        : {fila.get('nom', '—')} (Ubicació: {fila.get('lloc', '—')})\n"
            f"• DEPARTAMENT           : {fila.get('departament', '—')}\n"
            f"• DISPOSITIU            : {fila.get('dispositiu', '—')}\n"
            f"• CATEGORIA PRINCIPAL   : {fila.get('categoria', '—')}\n"
            f"• ABAST DE L'AFECTACIÓ  : {fila.get('abast', '—')}\n"
            f"• IMPACTE DETALLAT      : {impacte}\n"
            f"────────────────────────────────────────────────────────────────────────────────────────────\n"
            f"DESCRIPCIÓ FORENSE DEL PROBLEMA:\n"
            f"{fila.get('descripcio', 'Sense descripció informada.')}\n"
        )
        self.escriure_detall(dossier)

    def detall_descartada(self, _=None):
        sel = self.taula_descartades.selection()
        if not sel:
            return
        self.fer_so(600, 60)
        pos, motius = self.descartades[int(sel[0])]
        messagebox.showwarning(
            f"Anomalia en Registre XML #{pos}",
            f"Motius de descàrrega detectats:\n\n• " + "\n• ".join(motius),
        )

    def escriure_detall(self, text):
        self.txt_detall.configure(state="normal")
        self.txt_detall.delete("1.0", "end")
        self.txt_detall.insert("1.0", text)
        self.txt_detall.configure(state="disabled")

    # --- TELEMETRIA I GRÀFICS NEÓ ---
    def canviar_grafic(self, camp):
        self.fer_so(1150, 25)
        self.camp_grafic.set(camp)
        self.dibuixar_grafic()

    def dibuixar_grafic(self):
        c = self.colors
        can = self.canvas_grafic
        can.delete("all")
        amplada = max(can.winfo_width(), 650)

        if not self.visibles:
            can.create_text(
                amplada // 2, 80, text="No hi ha dades per mostrar amb els filtres actuals.",
                fill=c["suav"], font=(FONT_FAMILY, 11)
            )
            can.configure(scrollregion=(0, 0, amplada, 180))
            return

        comptadors, etiquetes = calcular_estadistiques(self.visibles)
        camp = self.camp_grafic.get()
        elements = sorted(
            comptadors[camp].items(),
            key=lambda x: (-x[1], etiquetes[camp][x[0]].casefold()),
        )
        total = len(self.visibles)

        if elements:
            top_k, top_q = elements[0]
            top_p = (top_q / total * 100)
            self.banner_insight.config(
                text=f"🏆 IMPACTE DOMINANT: {etiquetes[camp][top_k]} ({top_q:,} incidents • {top_p:.1f}% del conjunt filtrat)"
            )

        can.create_text(
            24, 20, anchor="nw", text=f"📊 TELEMETRIA // {ESTADISTIQUES[camp]}",
            fill=c["primari"], font=(FONT_FAMILY, 12, "bold")
        )

        y = 54
        ample_barra_max = max(180, amplada - 340)

        for clau, quantitat in elements:
            pct = quantitat / total * 100
            text_etiqueta = etiquetes[camp][clau]

            elem_text = can.create_text(
                24, y, anchor="nw", text=text_etiqueta, width=amplada - 70,
                fill=c["text"], font=(FONT_FAMILY, 10, "bold")
            )
            y = can.bbox(elem_text)[3] + 6

            # Barra fons
            can.create_rectangle(
                24, y, 24 + ample_barra_max, y + 18,
                fill=c["header"], outline=""
            )

            # Barra neó de progrés
            ample_pct = ample_barra_max * (pct / 100)
            can.create_rectangle(
                24, y, 24 + ample_pct, y + 18,
                fill=c["primari"], outline=""
            )

            # Dades numèriques
            can.create_text(
                36 + ample_barra_max, y + 9, anchor="w",
                text=f"{quantitat:,} reg.  ({pct:.1f}%)",
                fill=c["secundari"], font=(FONT_MONO, 9, "bold")
            )

            y += 42

        can.configure(scrollregion=(0, 0, amplada, y + 25))

    # --- REQUISIT F4: GESTIÓ I EXPORTACIÓ JSON ---
    def obrir_dialeg_json(self):
        if not self.acceptades:
            messagebox.showwarning("Atenció", "Primer cal carregar un fitxer XML amb dades vàlides.")
            return

        ruta_json = CARPETA_BASE / "incidencies.json"
        if ruta_json.exists():
            self.fer_so(900, 50)
            resposta = messagebox.askyesnocancel(
                "F4: Fitxer JSON Existent",
                f"El fitxer '{ruta_json.name}' ja existeix a la carpeta.\n\n"
                "• Clica [SÍ] per SOBREESCRIURE el fitxer complet.\n"
                "• Clica [NO] per AFEGIR les noves incidències sense duplicar per ID.\n"
                "• Clica [CANCEL·LAR] per aturar.",
                icon="question",
            )
            if resposta is True:
                self.executar_exportacio_json("overwrite")
            elif resposta is False:
                self.executar_exportacio_json("append")
        else:
            self.executar_exportacio_json("overwrite")

    def executar_exportacio_json(self, mode):
        if not self.acceptades:
            return

        ruta_json = CARPETA_BASE / "incidencies.json"
        try:
            res = exportar_json(self.acceptades, ruta_json, mode=mode)
            if res:
                self.fer_so(1600, 80)
                missatge = (
                    f"✔ Requisit F4 completat amb èxit!\n\n"
                    f"• Mode: {res['accio'].upper()}\n"
                    f"• Incidències noves afegides: {res['afegits']:,}\n"
                    f"• Duplicats ignorats: {res['duplicats_ignorats']:,}\n"
                    f"• Total al fitxer: {res['total_desats']:,} registres\n\n"
                    f"Ruta: {res['fitxer']}"
                )
                messagebox.showinfo("Exportació JSON OK", missatge)
                self.mostrar_preview_json()
                self.lbl_estat.config(text=f"✔ Fitxer JSON actualitzat: {res['total_desats']:,} registres totals.")
        except Exception as e:
            self.fer_so(400, 150)
            messagebox.showerror("Error F4 JSON", f"No s'ha pogut exportar: {e}")

    def mostrar_preview_json(self):
        ruta_json = CARPETA_BASE / "incidencies.json"
        if not ruta_json.exists():
            self.lbl_estat_json.config(text="Estat JSON: 'incidencies.json' encara no ha estat generat.", fg=self.colors["avís"])
            self.txt_json.delete("1.0", "end")
            self.txt_json.insert("1.0", "// El fitxer 'incidencies.json' no existeix.\n// Fes servir els botons superiors o la consola per generar-lo.")
            return

        try:
            mida_kb = ruta_json.stat().st_size / 1024
            mtime = datetime.fromtimestamp(ruta_json.stat().st_mtime).strftime("%d/%m/%Y %H:%M:%S")

            with open(ruta_json, "r", encoding="utf-8") as f:
                dades = json.load(f)

            num_reg = len(dades) if isinstance(dades, list) else 0
            self.lbl_estat_json.config(
                text=f"✔ Fitxer JSON actiu: {ruta_json.name} ({mida_kb:.1f} KB • {num_reg:,} incidències) • Modificat: {mtime}",
                fg=self.colors["ok"],
            )

            mostra = dades[:6] if isinstance(dades, list) else dades
            txt_json_mostra = json.dumps(mostra, indent=2, ensure_ascii=False)
            if isinstance(dades, list) and len(dades) > 6:
                txt_json_mostra += f"\n\n// ... i {len(dades) - 6} incidències més emmagatzemades en aquest fitxer."

            self.txt_json.delete("1.0", "end")
            self.txt_json.insert("1.0", txt_json_mostra)
        except Exception as e:
            self.lbl_estat_json.config(text=f"Error en llegir JSON: {e}", fg=self.colors["alerta"])

    def copiar_json_clipboard(self):
        ruta_json = CARPETA_BASE / "incidencies.json"
        if not ruta_json.exists():
            return
        try:
            with open(ruta_json, "r", encoding="utf-8") as f:
                contingut = f.read()
            self.clipboard_clear()
            self.clipboard_append(contingut)
            self.fer_so(1400, 40)
            messagebox.showinfo("Copia OK", "Tot el contingut JSON s'ha copiat al portapapers.")
        except Exception as e:
            messagebox.showerror("Error", f"No s'ha pogut copiar: {e}")

    def obrir_panell_web(self):
        script_web = CARPETA_BASE / "interfaz_web_pro.py"
        if not script_web.exists():
            messagebox.showwarning("Atenció", "No s'ha trobat 'interfaz_web_pro.py'.")
            return
        try:
            self.fer_so(1350, 40)
            subprocess.Popen([sys.executable, str(script_web)], cwd=str(CARPETA_BASE))
            self.lbl_estat.config(text="🌐 Panell Web Pro iniciat al navegador.")
        except Exception as e:
            messagebox.showerror("Error", f"No s'ha pogut iniciar el servidor web: {e}")


if __name__ == "__main__":
    app = AplicacioAbsoluteCinema()
    app.mainloop()
