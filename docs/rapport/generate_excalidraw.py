#!/usr/bin/env python3
"""Generate Excalidraw diagrams for the PFE report."""

import json, time, random

r = random.Random(42)

ELEM = []

def _id():
    return f"elem-{len(ELEM):04d}"

def rect(x, y, w, h, label="", fill="transparent", stroke="#1e1e1e", sw=2, rness=1, dash=[], font_size=20):
    eid = _id()
    ELEM.append({
        "id": eid,
        "type": "rectangle",
        "x": x, "y": y, "width": w, "height": h,
        "angle": 0,
        "strokeColor": stroke,
        "backgroundColor": fill,
        "fillStyle": "solid",
        "strokeWidth": sw,
        "strokeStyle": "solid" if not dash else "dashed",
        "roughness": rness,
        "opacity": 100,
        "groupIds": [],
        "roundness": {"type": 3},
        "seed": r.randint(0, 2**30),
        "version": 1,
        "isDeleted": False,
        "boundElements": None,
        "updated": int(time.time()*1000),
        "link": None,
        "locked": False,
    })
    return eid

def text(x, y, txt, size=20, align="center", color="#1e1e1e", bold=False, w=None):
    eid = _id()
    lines = txt.split("\n")
    h = size * len(lines) * 1.2
    ELEM.append({
        "id": eid,
        "type": "text",
        "x": x, "y": y,
        "width": w or size * max(len(l) for l in lines) * 0.6,
        "height": h,
        "angle": 0,
        "strokeColor": color,
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "roundness": None,
        "seed": r.randint(0, 2**30),
        "version": 1,
        "isDeleted": False,
        "boundElements": None,
        "updated": int(time.time()*1000),
        "link": None,
        "locked": False,
        "text": txt,
        "fontSize": size,
        "fontFamily": 1,
        "textAlign": align,
        "verticalAlign": "middle",
        "containerId": None,
        "originalText": txt,
        "autoResize": True,
        "lineHeight": 1.2,
    })
    return eid

def arrow(x1, y1, x2, y2, color="#1e1e1e", sw=2, dash=[]):
    eid = _id()
    ELEM.append({
        "id": eid,
        "type": "arrow",
        "x": x1, "y": y1,
        "width": abs(x2-x1),
        "height": abs(y2-y1),
        "angle": 0,
        "strokeColor": color,
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": sw,
        "strokeStyle": "solid" if not dash else "dashed",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "roundness": {"type": 2},
        "seed": r.randint(0, 2**30),
        "version": 1,
        "isDeleted": False,
        "boundElements": None,
        "updated": int(time.time()*1000),
        "link": None,
        "locked": False,
        "points": [[0, 0], [x2-x1, y2-y1]],
        "lastCommittedPoint": None,
        "startBinding": None,
        "endBinding": None,
        "startArrowhead": None,
        "endArrowhead": "arrow",
    })
    return eid

def line(pts, color="#1e1e1e", sw=2, dash=[]):
    eid = _id()
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    ELEM.append({
        "id": eid,
        "type": "line",
        "x": min(xs), "y": min(ys),
        "width": max(xs)-min(xs),
        "height": max(ys)-min(ys),
        "angle": 0,
        "strokeColor": color,
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": sw,
        "strokeStyle": "solid" if not dash else "dashed",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "roundness": {"type": 2},
        "seed": r.randint(0, 2**30),
        "version": 1,
        "isDeleted": False,
        "boundElements": None,
        "updated": int(time.time()*1000),
        "link": None,
        "locked": False,
        "points": [[p[0]-min(xs), p[1]-min(ys)] for p in pts],
        "lastCommittedPoint": None,
        "startBinding": None,
        "endBinding": None,
        "startArrowhead": None,
        "endArrowhead": None,
    })
    return eid


def generate_cycle_v():
    global ELEM
    ELEM = []
    bw, bh = 260, 70   # box width/height
    cw = bw // 2

    # Left side boxes - descending
    left_items = [
        (80,  60,  "Spécifications\nGénérales"),
        (160, 200, "Spécifications\nFonctionnelles"),
        (240, 340, "Architecture\nSystème"),
        (320, 480, "Conception\nDétaillée"),
    ]
    right_items = [
        (780, 480, "Tests\nUnitaires"),
        (860, 340, "Tests\nd'Intégration"),
        (940, 200, "Tests\nd'Acceptation"),
        (1020, 60, "Validation"),
    ]
    bottom = (480, 620, "Implémentation & Codage")

    # Draw V lines
    left_last = (left_items[-1][0]+bw, left_items[-1][1]+bh//2)
    right_first = (right_items[0][0], right_items[0][1]+bh//2)
    line_pts = [
        (left_items[0][0], left_items[0][1]+bh//2),       # top-left
        (left_last[0], left_items[0][1]+bh//2),
        left_last,                                          # bottom-left
        right_first,                                        # bottom-right
        (right_first[0], right_items[-1][1]+bh//2),
        (right_items[-1][0]+bw, right_items[-1][1]+bh//2), # top-right
    ]
    line(line_pts, color="#2d6a4f", sw=3)

    # Arrows from left to right
    for li, ri in zip(left_items, right_items):
        lx = li[0] + bw
        ly = li[1] + bh//2
        rx = ri[0]
        ry = ri[1] + bh//2
        arrow(lx, ly, rx, ry, color="#d00000", sw=2, dash=[8, 6])

    # Draw left boxes + text
    for x, y, title in left_items:
        rect(x, y, bw, bh, fill="#e0fbfc", stroke="#0077b6")
        text(x+10, y+8, title, size=18, align="left", color="#023e8a")

    # Draw right boxes + text
    for x, y, title in right_items:
        rect(x, y, bw, bh, fill="#e0fbfc", stroke="#0077b6")
        text(x+10, y+8, title, size=18, align="left", color="#023e8a")

    # Bottom box
    bx, by, btitle = bottom
    rect(bx, by, 440, bh, fill="#ccffd6", stroke="#2d6a4f")
    text(bx+20, by+15, btitle, size=22, align="left", color="#1b4332", bold=True)

    # Title
    text(400, 10, "Cycle en V du système de supervision thermique", size=26, bold=True, color="#1e1e1e")

    # --- Tableau des livrables ---
    table_y = 740
    col_w = [60, 260, 400]
    table_w = sum(col_w)
    table_x = 120
    rh = 32  # row height

    livrables = [
        ("1", "Spécifications Générales", "Cahier des charges, besoins fonctionnels"),
        ("2", "Spécifications Fonctionnelles", "AMDEC, règles métier de classification N1"),
        ("3", "Architecture Système", "Schéma pipeline acquisition–diagnostic–prédiction"),
        ("4", "Conception Détaillée", "Diagrammes UML des modules (Modbus, Grey-Box, IF, RF, Ridge)"),
        ("5", "Implémentation & Codage", "Code backend Python + ML scikit-learn + frontend React"),
        ("6", "Tests Unitaires", "35 tests unitaires, 5 modules, rapport de couverture"),
        ("7", "Tests d'Intégration", "Pipeline complet validé (acquisition → stockage → diffusion)"),
        ("8", "Tests d'Acceptation", "Prototype laboratoire conforme au cahier des charges"),
        ("9", "Validation & Déploiement", "Rapport de validation, script setup_rpi.sh, services systemd"),
    ]

    # Table header
    hdr_fill = "#023e8a"
    hdr_txt = "#ffffff"
    rect(table_x, table_y, col_w[0], rh, fill=hdr_fill, stroke=hdr_fill, sw=1, rness=0)
    rect(table_x+col_w[0], table_y, col_w[1], rh, fill=hdr_fill, stroke=hdr_fill, sw=1, rness=0)
    rect(table_x+col_w[0]+col_w[1], table_y, col_w[2], rh, fill=hdr_fill, stroke=hdr_fill, sw=1, rness=0)
    text(table_x+20, table_y+6, "N°", size=14, align="left", color=hdr_txt, bold=True)
    text(table_x+col_w[0]+20, table_y+6, "Phase", size=14, align="left", color=hdr_txt, bold=True)
    text(table_x+col_w[0]+col_w[1]+20, table_y+6, "Livrable", size=14, align="left", color=hdr_txt, bold=True)

    # Table rows
    for idx, (num, phase, livr) in enumerate(livrables):
        ry = table_y + rh + idx * rh
        bg = "#f0f8ff" if idx % 2 == 0 else "#ffffff"
        rect(table_x, ry, col_w[0], rh, fill=bg, stroke="#c0c0c0", sw=1, rness=0)
        rect(table_x+col_w[0], ry, col_w[1], rh, fill=bg, stroke="#c0c0c0", sw=1, rness=0)
        rect(table_x+col_w[0]+col_w[1], ry, col_w[2], rh, fill=bg, stroke="#c0c0c0", sw=1, rness=0)
        text(table_x+10, ry+6, num, size=13, align="left", color="#023e8a", bold=True)
        text(table_x+col_w[0]+10, ry+6, phase, size=13, align="left", color="#1e1e1e")
        text(table_x+col_w[0]+col_w[1]+10, ry+6, livr, size=13, align="left", color="#1e1e1e")

    # Table caption
    text(table_x, table_y + rh + len(livrables)*rh + 5, "Tableau 1 : Correspondance Cycle en V — Livrables", size=14, align="left", color="#666666", bold=False)

    return {"type": "excalidraw", "version": 2, "source": "custom", "elements": ELEM, "appState": { "gridSize": None, "viewBackgroundColor": "#ffffff" }}


def generate_gantt():
    global ELEM
    ELEM = []
    bh = 28
    start_y = 120
    x0 = 200
    col_w = 80

    phases = [
        ("Analyse des besoins & AMDEC",         0, 2),
        ("Conception architecture système",      1, 2),
        ("Développement acquisition Modbus",     1, 2),
        ("Développement Grey-Box & IF",          2, 2),
        ("Développement classifieur N1/N2",      2, 2),
        ("Développement Ridge Regression",       3, 1),
        ("Développement système d'alertes",      3, 1),
        ("Développement frontend React",         1, 4),
        ("Tests unitaires (35 tests)",           3, 2),
        ("Tests d'intégration",                  4, 1),
        ("Tests d'acceptation (laboratoire)",    4, 1),
        ("Rédaction du rapport",                 2, 3),
    ]

    months = ["Fév", "Mars", "Avr", "Mai", "Juin"]
    total_months = 5

    # Header
    text(40, 80, "Phases", size=16, bold=True)
    for i, m in enumerate(months):
        if i >= total_months: break
        text(x0 + i*col_w + col_w//3, 80, m, size=13, align="center", color="#1e1e1e")

    # Grid lines
    for i in range(total_months+1):
        lx = x0 + i*col_w
        line([(lx, 105), (lx, start_y + len(phases)*bh + 20)], color="#d0d0d0", sw=1, dash=[4,4])

    # Phases
    colors = ["#0077b6", "#023e8a", "#2d6a4f", "#52b788", "#e07a5f", "#d62828",
              "#7209b7", "#f77f00", "#fcbf49", "#eae2b7", "#a8dadc", "#457b9d"]

    for idx, (name, start, dur) in enumerate(phases):
        y = start_y + idx * bh
        # Phase name
        text(20, y-2, name, size=13, align="left", color="#1e1e1e")
        # Bar
        bx = x0 + start * col_w
        bw = dur * col_w
        c = colors[idx % len(colors)]
        rect(bx, y, bw, bh-4, fill=c, stroke=c, sw=1, rness=0)
        # Month labels
        for m in range(start, start+dur):
            if m <= total_months-1:
                lx = x0 + m * col_w + col_w//2
                line([(lx, y), (lx, y+bh-4)], color="white", sw=1, dash=[2,4])

    # Title
    text(200, 20, "Diagramme de Gantt du projet", size=26, bold=True, color="#1e1e1e")

    return {"type": "excalidraw", "version": 2, "source": "custom", "elements": ELEM, "appState": { "gridSize": None, "viewBackgroundColor": "#ffffff" }}


if __name__ == "__main__":
    with open("Cycle_en_V.excalidraw", "w", encoding="utf-8") as f:
        json.dump(generate_cycle_v(), f, indent=2)
    with open("Diagramme_Gantt.excalidraw", "w", encoding="utf-8") as f:
        json.dump(generate_gantt(), f, indent=2)
    print("Done: Cycle_en_V.excalidraw, Diagramme_Gantt.excalidraw")
