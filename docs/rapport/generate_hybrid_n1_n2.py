#!/usr/bin/env python3
"""Generate Excalidraw diagram for the hybrid N1/N2 architecture."""

import json, time, random, os

r = random.Random(42)
ELEM = []

def _id():
    return f"elem-{len(ELEM):04d}"

def rect(x, y, w, h, label="", fill="transparent", stroke="#1e1e1e", sw=2):
    eid = _id()
    ELEM.append({
        "id": eid, "type": "rectangle", "x": x, "y": y, "width": w, "height": h,
        "angle": 0, "strokeColor": stroke, "backgroundColor": fill, "fillStyle": "solid",
        "strokeWidth": sw, "strokeStyle": "solid", "roughness": 1, "opacity": 100,
        "groupIds": [], "roundness": {"type": 3},
        "seed": r.randint(0, 2**30), "version": 1, "isDeleted": False,
        "boundElements": [], "updated": int(time.time()*1000), "link": None, "locked": False,
    })
    return eid

def text(x, y, txt, size=20, align="center", color="#1e1e1e", bold=False):
    eid = _id()
    lines = txt.split("\n")
    h = size * len(lines) * 1.2
    ELEM.append({
        "id": eid, "type": "text", "x": x, "y": y,
        "width": size * max(len(l) for l in lines) * 0.6,
        "height": h, "angle": 0, "strokeColor": color, "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": 2, "roughness": 1, "opacity": 100,
        "groupIds": [], "roundness": None,
        "seed": r.randint(0, 2**30), "version": 1, "isDeleted": False,
        "boundElements": [], "updated": int(time.time()*1000), "link": None, "locked": False,
        "text": txt, "fontSize": size, "fontFamily": 1, "textAlign": align,
        "verticalAlign": "middle", "containerId": None, "originalText": txt,
        "autoResize": True, "lineHeight": 1.2,
    })
    return eid

def arrow(x1, y1, x2, y2, color="#1e1e1e", sw=2, label=""):
    eid = _id()
    ELEM.append({
        "id": eid, "type": "arrow", "x": x1, "y": y1,
        "width": abs(x2-x1), "height": abs(y2-y1), "angle": 0,
        "strokeColor": color, "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": sw, "strokeStyle": "solid",
        "roughness": 1, "opacity": 100, "groupIds": [],
        "roundness": {"type": 2}, "seed": r.randint(0, 2**30), "version": 1,
        "isDeleted": False, "boundElements": [], "updated": int(time.time()*1000),
        "link": None, "locked": False,
        "points": [[0, 0], [x2-x1, y2-y1]], "lastCommittedPoint": None,
        "startBinding": None, "endBinding": None,
        "startArrowhead": None, "endArrowhead": "arrow",
    })
    return eid

def line(pts, color="#1e1e1e", sw=2, dash=[]):
    eid = _id()
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    ELEM.append({
        "id": eid, "type": "line", "x": min(xs), "y": min(ys),
        "width": max(xs)-min(xs), "height": max(ys)-min(ys),
        "angle": 0, "strokeColor": color, "backgroundColor": "transparent",
        "fillStyle": "solid", "strokeWidth": sw, "strokeStyle": "solid" if not dash else "dashed",
        "roughness": 1, "opacity": 100, "groupIds": [],
        "roundness": {"type": 2}, "seed": r.randint(0, 2**30), "version": 1,
        "isDeleted": False, "boundElements": [], "updated": int(time.time()*1000),
        "link": None, "locked": False,
        "points": [[p[0]-min(xs), p[1]-min(ys)] for p in pts],
        "lastCommittedPoint": None, "startBinding": None, "endBinding": None,
        "startArrowhead": None, "endArrowhead": None,
    })
    return eid

def generate():
    global ELEM
    ELEM = []
    bw, bh = 200, 60
    cx = 400
    gap_y = 90

    # Colors
    blue = "#e0fbfc"
    blue_stroke = "#0077b6"
    green = "#ccffd6"
    green_stroke = "#2d6a4f"
    orange = "#fff3e0"
    orange_stroke = "#e65100"
    gray = "#f5f5f5"
    gray_stroke = "#616161"

    # Title
    text(200, 20, "Architecture hybride de classification des causes (N1/N2)", size=24, bold=True, color="#1e1e1e")

    # === Row 0: Sensors ===
    y0 = 80
    r1 = rect(300, y0, 200, bh, fill=blue, stroke=blue_stroke)
    text(310, y0+15, "Capteurs\n(température, débit)", size=16, align="left", color="#023e8a")

    # === Row 1: Feature extraction ===
    y1 = y0 + bh + gap_y
    r2 = rect(300, y1, 200, bh, fill=blue, stroke=blue_stroke)
    text(310, y1+15, "Extraction features\n(8 carac., fenêtre 30s)", size=15, align="left", color="#023e8a")
    arrow(cx, y0+bh, cx, y1, sw=2)

    # === Row 2: IF Decision ===
    y2 = y1 + bh + gap_y
    r3 = rect(300, y2, 200, bh, fill=blue, stroke=blue_stroke)
    text(310, y2+15, "Isolation Forest\nscore < 0,5 ?", size=16, align="left", color="#023e8a")
    arrow(cx, y1+bh, cx, y2, sw=2)

    # === Row 3a: Normal (right side) ===
    y3 = y2 + bh + gap_y
    rx3 = 550
    r4 = rect(rx3, y3, 160, bh, fill=green, stroke=green_stroke)
    text(rx3+10, y3+15, "NORMAL\n(OK)", size=18, align="left", color="#1b4332", bold=True)

    # Arrow IF → NORMAL (dashed, rightwards)
    arrow(cx+bw//2, y2+bh//2, rx3, y3+bh//2, color=green_stroke, sw=2)

    # Label on the arrow
    text(cx+bw//2+40, y3-10, "Non (score ≥ 0,5)", size=13, align="center", color="#2d6a4f")

    # === Row 3b: Anomaly (left side) ===
    lx3 = 60
    r5 = rect(lx3, y3, 200, bh, fill=orange, stroke=orange_stroke)
    text(lx3+10, y3+15, "Anomalie détectée", size=18, align="left", color="#bf360c", bold=True)

    # Arrow IF → Anomaly (leftwards)
    arrow(cx-bw//2, y2+bh//2, lx3+bw, y3+bh//2, color=orange_stroke, sw=2)
    text(lx3+bw+20, y3-10, "Oui (score < 0,5)", size=13, align="center", color="#e65100")

    # === Row 4: N1 Physical Rules ===
    y4 = y3 + bh + gap_y
    r6 = rect(lx3, y4, 200, bh, fill=green, stroke=green_stroke)
    text(lx3+10, y4+15, "N1 — Règles physiques\n(4 règles déterministes)", size=15, align="left", color="#1b4332")
    arrow(lx3+bw//2, y3+bh, lx3+bw//2, y4, sw=2)

    # === Row 5a: N1 Certain (left) ===
    y5 = y4 + bh + gap_y
    lx5 = 20
    r7 = rect(lx5, y5, 200, bh, fill=green, stroke=green_stroke)
    text(lx5+10, y5+15, "Cause certaine\nconfiance = 1,0", size=16, align="left", color="#1b4332", bold=True)

    # Arrow N1 → Certain
    arrow(lx3+bw//2-40, y4+bh, lx5+bw//2, y5, sw=2)
    text(lx3-10, y4+bh//2+50, "Règle\nappliquée", size=12, align="center", color="#2d6a4f")

    # === Row 5b: N2 Random Forest (right) ===
    rx5 = 350
    r8 = rect(rx5, y5, 220, bh, fill=blue, stroke=blue_stroke)
    text(rx5+10, y5+15, "N2 — Random Forest\n(10 carac., 100 arbres)", size=15, align="left", color="#023e8a")

    # Arrow N1 → N2
    arrow(lx3+bw//2+40, y4+bh, rx5, y5+bh//2, color=blue_stroke, sw=2)
    text(rx5-120, y4+bh//2+40, "Aucune règle\napplicable", size=12, align="center", color="#0077b6")

    # === Row 6: N2 Output ===
    y6 = y5 + bh + gap_y
    r9 = rect(rx5, y6, 220, bh, fill=blue, stroke=blue_stroke)
    text(rx5+10, y6+15, "Cause classifiée\n(confiance ≥ 0,5)", size=16, align="left", color="#023e8a")
    arrow(rx5+bw//2+10, y5+bh, rx5+bw//2+10, y6, sw=2)

    # Legend
    ly = y6 + bh + 40
    line([(60, ly), (120, ly)], color="#e65100", sw=3)
    text(130, ly-10, "N1 (règles physiques, certitude 1,0)", size=14, align="left", color="#1e1e1e")

    line([(60, ly+30), (120, ly+30)], color="#0077b6", sw=3)
    text(130, ly+20, "N2 (Random Forest, confiance ≥ 0,5)", size=14, align="left", color="#1e1e1e")

    line([(60, ly+60), (120, ly+60)], color="#2d6a4f", sw=3)
    text(130, ly+50, "Chemin normal (aucune anomalie)", size=14, align="left", color="#1e1e1e")

    return {"type": "excalidraw", "version": 2, "source": "custom", "elements": ELEM,
            "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"}}

if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "Architecture_N1_N2.excalidraw")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(generate(), f, indent=2)
    print(f"Generated {out}")
