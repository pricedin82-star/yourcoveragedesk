#!/usr/bin/env python3
"""Renderiza los slides del carrusel de la siguiente pieza del banco.

Toma la primera pieza de contenido/banco.json que no esté en
contenido/estado.json y produce PNGs de 1080x1350 con la identidad de la marca:
asfalto de fondo, titular en Anton, el dato clave en ámbar.

Uso:
    python scripts/build_carrusel.py --out build
"""
import argparse
import json
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def buscar(*candidatos):
    """Encuentra un archivo tanto si el repo tiene carpetas como si está plano.

    GitHub aplana la estructura cuando se arrastran carpetas al navegador, así
    que el mismo código funciona en los dos casos sin tocar nada.
    """
    from pathlib import Path as _P
    for c in candidatos:
        if _P(c).exists():
            return str(c)
    return str(candidatos[-1])

W, H = 1080, 1350
ASF = (20, 20, 15)
AMBER = (242, 169, 0)
WHITE = (245, 242, 234)
MUTED = (150, 146, 132)
LINE = (58, 56, 48)
MARGIN = 88


def cargar_fuente(ruta, tam):
    try:
        return ImageFont.truetype(ruta, tam)
    except OSError as e:
        raise SystemExit(
            f"No se encontró la fuente {ruta}. En GitHub Actions la descarga el workflow; "
            f"en local, pon los .ttf en assets/fuentes/. ({e})"
        )


def alto_texto(draw, texto, fuente, ancho_max, interlineado):
    lineas = envolver(draw, texto, fuente, ancho_max)
    return len(lineas) * interlineado, lineas


def envolver(draw, texto, fuente, ancho_max):
    """Envuelve respetando los saltos de línea que ya trae el texto."""
    salida = []
    for parrafo in texto.split("\n"):
        if not parrafo.strip():
            salida.append("")
            continue
        palabras, linea = parrafo.split(), ""
        for p in palabras:
            prueba = f"{linea} {p}".strip()
            if draw.textlength(prueba, font=fuente) <= ancho_max:
                linea = prueba
            else:
                if linea:
                    salida.append(linea)
                linea = p
        if linea:
            salida.append(linea)
    return salida


def render_slide(slide, idx, total, badge, handle, fuentes, size=None, paginar=True, base_ratio=None):
    w, h = size or (W, H)
    img = Image.new("RGB", (w, h), ASF)
    d = ImageDraw.Draw(img)
    f_tit, f_sub, f_mono, f_dato = fuentes
    ancho = w - MARGIN * 2

    # --- badge arriba a la izquierda ---
    d.rectangle([MARGIN, 70, MARGIN + int(d.textlength(badge, font=f_mono)) + 34, 70 + 42],
                fill=(45, 95, 124) if badge == "COMMERCIAL" else (60, 46, 12))
    d.text((MARGIN + 17, 80), badge, font=f_mono, fill=AMBER if badge != "COMMERCIAL" else WHITE)

    # --- círculo con el dato clave, arriba a la derecha ---
    dato = slide.get("dato")
    if dato:
        r = 78
        cx, cy = w - MARGIN - r, 70 + r
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=AMBER, width=6)
        tw = d.textlength(dato, font=f_dato)
        bbox = f_dato.getbbox(dato)
        d.text((cx - tw / 2, cy - (bbox[3] - bbox[1]) / 2 - bbox[1]), dato, font=f_dato, fill=AMBER)

    # --- bloque de texto, anclado abajo ---
    titulo = slide["titulo"].upper()
    sub = slide.get("sub", "")
    il_tit, il_sub = 96, 46

    h_tit, lin_tit = alto_texto(d, titulo, f_tit, ancho, il_tit)
    h_sub, lin_sub = alto_texto(d, sub, f_sub, ancho, il_sub) if sub else (0, [])

    # En vertical el bloque sube: abajo del todo lo tapan los botones de la app.
    base = int(h * base_ratio) if base_ratio else h - 150
    y = base - h_sub - (34 if sub else 0) - h_tit

    # Regla ámbar sobre el titular: ancla la vista y marca la identidad.
    d.rectangle([MARGIN, y - 46, MARGIN + 96, y - 40], fill=AMBER)

    for ln in lin_tit:
        d.text((MARGIN, y), ln, font=f_tit, fill=WHITE)
        y += il_tit
    if sub:
        y += 34
        for ln in lin_sub:
            d.text((MARGIN, y), ln, font=f_sub, fill=MUTED)
            y += il_sub

    # --- pie: handle y paginación ---
    d.line([MARGIN, h - 96, w - MARGIN, h - 96], fill=LINE, width=2)
    d.text((MARGIN, h - 74), handle, font=f_mono, fill=MUTED)
    if paginar:
        pag = f"{idx + 1}/{total}"
        d.text((w - MARGIN - d.textlength(pag, font=f_mono), h - 74), pag, font=f_mono, fill=MUTED)
    return img


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="build")
    p.add_argument("--fuentes", default="assets/fuentes")
    p.add_argument("--handle", default="@yourcoveragedesk")
    p.add_argument("--pieza", help="Forzar una pieza por id (para pruebas)")
    args = p.parse_args()

    banco = json.loads(Path(buscar("contenido/banco.json", "banco.json")).read_text())["piezas"]
    estado = json.loads(Path(buscar("contenido/estado.json", "estado.json")).read_text())
    hechas = set(estado.get("publicadas", []))

    if args.pieza:
        pieza = next((x for x in banco if x["id"] == args.pieza), None)
        if not pieza:
            raise SystemExit(f"No existe la pieza {args.pieza}")
    else:
        pieza = next((x for x in banco if x["id"] not in hechas), None)
        if not pieza:
            raise SystemExit("BANCO_VACIO: no quedan piezas sin publicar. Añade más a banco.json.")

    fd = args.fuentes
    anton = buscar(f"{fd}/Anton-Regular.ttf", "Anton-Regular.ttf")
    dvs = buscar(f"{fd}/DejaVuSans.ttf", "DejaVuSans.ttf")
    dvb = buscar(f"{fd}/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf")
    fuentes = (
        cargar_fuente(anton, 80),
        cargar_fuente(dvs, 34),
        cargar_fuente(dvb, 22),
        cargar_fuente(anton, 46),
    )

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    slides = pieza["slides"]
    rutas = []
    for i, s in enumerate(slides):
        img = render_slide(s, i, len(slides), pieza.get("badge", "COVERAGE 101"), args.handle, fuentes)
        ruta = out / f"slide_{i + 1:02d}.jpg"
        img.convert("RGB").save(ruta, "JPEG", quality=92)
        rutas.append(str(ruta))
        print(f"  {ruta}")

    caption = pieza["caption"] + "\n\n" + " ".join(pieza.get("hashtags", []))
    (out / "caption.txt").write_text(caption)
    (out / "pieza.json").write_text(json.dumps(
        {"id": pieza["id"], "tema": pieza["tema"], "slides": rutas}, indent=2, ensure_ascii=False))

    print(f"\nPieza: {pieza['id']} — {pieza['tema']}")
    print(f"{len(rutas)} slides en {out}/")


if __name__ == "__main__":
    main()
