#!/usr/bin/env python3
"""Construye el Reel vertical a partir del mismo banco de contenido.

Este archivo es AUTÓNOMO a propósito: no importa nada de build_carrusel.py.
Así el Reel funciona aunque el otro script esté en otra versión, y solo hay
que subir este archivo para tener Reels.

El Reel es el mismo carrusel en vertical, con voz y un zoom lento. La voz la
genera Piper, que corre local en la máquina de GitHub: sin clave y sin costo.

Uso:
    python build_reel.py --out build_reel --voz voces/en_US-ryan-high.onnx
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
ASF = (20, 20, 15)
AMBER = (242, 169, 0)
WHITE = (245, 242, 234)
MUTED = (150, 146, 132)
LINE = (58, 56, 48)
SLATE = (45, 95, 124)
MARGIN = 88
BASE_Y = 0.72        # el bloque de texto acaba aquí: abajo lo tapan los botones
PAD = 0.45           # silencio tras cada frase
MIN_SLIDE = 2.2      # ningún plano baja de esto


def buscar(*candidatos):
    """Encuentra un archivo tanto si el repo tiene carpetas como si está plano."""
    for c in candidatos:
        if Path(c).exists():
            return str(c)
    return str(candidatos[-1])


def fuente(ruta, tam):
    try:
        return ImageFont.truetype(ruta, tam)
    except OSError as e:
        raise SystemExit(f"No se encontró la fuente {ruta}. ({e})")


def envolver(draw, texto, f, ancho):
    """Envuelve respetando los saltos de línea que ya trae el texto."""
    salida = []
    for parrafo in texto.split("\n"):
        if not parrafo.strip():
            salida.append("")
            continue
        linea = ""
        for p in parrafo.split():
            prueba = f"{linea} {p}".strip()
            if draw.textlength(prueba, font=f) <= ancho:
                linea = prueba
            else:
                if linea:
                    salida.append(linea)
                linea = p
        if linea:
            salida.append(linea)
    return salida


def tarjeta(slide, badge, handle, fs):
    f_tit, f_sub, f_mono, f_dato = fs
    img = Image.new("RGB", (W, H), ASF)
    d = ImageDraw.Draw(img)
    ancho = W - MARGIN * 2

    col_badge = SLATE if badge == "COMMERCIAL" else (60, 46, 12)
    col_txt = WHITE if badge == "COMMERCIAL" else AMBER
    ancho_badge = int(d.textlength(badge, font=f_mono)) + 34
    d.rectangle([MARGIN, 76, MARGIN + ancho_badge, 76 + 48], fill=col_badge)
    d.text((MARGIN + 17, 88), badge, font=f_mono, fill=col_txt)

    dato = slide.get("dato")
    if dato:
        r = 92
        cx, cy = W - MARGIN - r, 76 + r
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=AMBER, width=7)
        tw = d.textlength(dato, font=f_dato)
        bb = f_dato.getbbox(dato)
        d.text((cx - tw / 2, cy - (bb[3] - bb[1]) / 2 - bb[1]), dato, font=f_dato, fill=AMBER)

    titulo = slide["titulo"].upper()
    sub = slide.get("sub", "")
    il_tit, il_sub = 122, 56
    lin_tit = envolver(d, titulo, f_tit, ancho)
    lin_sub = envolver(d, sub, f_sub, ancho) if sub else []
    h_tit, h_sub = len(lin_tit) * il_tit, len(lin_sub) * il_sub

    y = int(H * BASE_Y) - h_sub - (40 if sub else 0) - h_tit
    d.rectangle([MARGIN, y - 56, MARGIN + 112, y - 48], fill=AMBER)
    for ln in lin_tit:
        d.text((MARGIN, y), ln, font=f_tit, fill=WHITE)
        y += il_tit
    if sub:
        y += 40
        for ln in lin_sub:
            d.text((MARGIN, y), ln, font=f_sub, fill=MUTED)
            y += il_sub

    d.line([MARGIN, H - 130, W - MARGIN, H - 130], fill=LINE, width=2)
    d.text((MARGIN, H - 104), handle, font=f_mono, fill=MUTED)
    return img


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write((r.stderr or "")[-1500:] + "\n")
        raise SystemExit(f"Falló: {' '.join(cmd[:5])} ...")


def narracion(slide):
    """El titular trae saltos de línea para el diseño; para la voz se aplanan."""
    tit = re.sub(r"\s+", " ", slide["titulo"]).strip()
    sub = re.sub(r"\s+", " ", slide.get("sub", "")).strip()
    if tit and tit[-1] not in ".!?":
        tit += "."
    return f"{tit} {sub}".strip()


def dur_wav(p):
    with wave.open(str(p)) as w:
        return w.getnframes() / w.getframerate()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="build_reel")
    p.add_argument("--voz", required=True)
    p.add_argument("--fuentes", default="assets/fuentes")
    p.add_argument("--handle", default="@yourcoveragedesk")
    p.add_argument("--pieza")
    args = p.parse_args()

    if not shutil.which("ffmpeg"):
        raise SystemExit("Falta ffmpeg en el PATH.")
    if not Path(args.voz).exists():
        raise SystemExit(f"No existe el modelo de voz {args.voz}.")

    banco = json.loads(Path(buscar("contenido/banco.json", "banco.json")).read_text())["piezas"]
    estado = json.loads(Path(buscar("contenido/estado.json", "estado.json")).read_text())
    hechas = set(estado.get("publicadas_reel", []))

    if args.pieza:
        pieza = next((x for x in banco if x["id"] == args.pieza), None)
        if not pieza:
            raise SystemExit(f"No existe la pieza {args.pieza}")
    else:
        # Al revés que el carrusel: así la misma pieza no sale en los dos
        # formatos la misma semana.
        pieza = next((x for x in reversed(banco) if x["id"] not in hechas), None)
        if not pieza:
            raise SystemExit("BANCO_VACIO: no quedan piezas para Reel.")

    fd = args.fuentes
    anton = buscar(f"{fd}/Anton-Regular.ttf", "Anton-Regular.ttf")
    dvs = buscar(f"{fd}/DejaVuSans.ttf", "DejaVuSans.ttf")
    dvb = buscar(f"{fd}/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf")
    fs = (fuente(anton, 104), fuente(dvs, 42), fuente(dvb, 26), fuente(anton, 58))

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    tmp = out / "tmp"
    tmp.mkdir()

    clips, total = [], 0.0
    slides = pieza["slides"]
    for i, s in enumerate(slides):
        wav = tmp / f"voz_{i:02d}.wav"
        r = subprocess.run([sys.executable, "-m", "piper", "-m", args.voz, "-f", str(wav)],
                           input=narracion(s), capture_output=True, text=True)
        if r.returncode != 0 or not wav.exists():
            sys.stderr.write((r.stderr or "")[-800:] + "\n")
            raise SystemExit(f"Piper falló en el slide {i + 1}.")
        dur = max(dur_wav(wav) + PAD, MIN_SLIDE)
        total += dur

        png = tmp / f"card_{i:02d}.png"
        tarjeta(s, pieza.get("badge", "COVERAGE 101"), args.handle, fs).save(png)

        clip = tmp / f"clip_{i:02d}.mp4"
        fps, frames = 30, int(dur * 30)
        zoom = f"zoompan=z='min(zoom+0.0006,1.09)':d={frames}:s={W}x{H}:fps={fps}"
        run(["ffmpeg", "-y", "-loop", "1", "-i", str(png), "-i", str(wav),
             "-t", f"{dur}", "-vf", f"scale={W*2}:{H*2},{zoom},format=yuv420p",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
             "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-shortest", str(clip)])
        clips.append(clip)
        print(f"  slide {i + 1}/{len(slides)}  {dur:.1f}s")

    lista = tmp / "concat.txt"
    lista.write_text("".join(f"file '{c.resolve()}'\n" for c in clips))
    reel = out / "reel.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lista),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
         "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(reel)])
    run(["ffmpeg", "-y", "-i", str(reel), "-ss", "0.5", "-vframes", "1",
         "-q:v", "2", str(out / "portada.jpg")])

    (out / "caption.txt").write_text(
        pieza["caption"] + "\n\n" + " ".join(pieza.get("hashtags", [])))
    (out / "pieza.json").write_text(json.dumps(
        {"id": pieza["id"], "tema": pieza["tema"], "duracion": round(total, 1)},
        indent=2, ensure_ascii=False))

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nPieza: {pieza['id']} — {pieza['tema']}")
    print(f"{reel}  ({total:.1f}s)")
    if total < 15:
        print("AVISO: menos de 15s; Instagram lo admite pero rinde peor.", file=sys.stderr)


if __name__ == "__main__":
    main()
