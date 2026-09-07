#!/usr/bin/env python3
"""Construye el Reel vertical de la misma pieza que el carrusel.

La idea: el Reel ES el carrusel, animado y con voz. Mismo banco de contenido,
mismos textos, cero material nuevo que escribir. Lo único que cambia es el
formato (1080x1920), la voz encima y un zoom lento en cada tarjeta.

La voz la genera Piper, que corre local en la propia máquina de GitHub Actions:
sin clave, sin costo y sin depender de ningún servicio que pueda caerse o
cambiar de precio.

Uso:
    python build_reel.py --out build_reel --voz en_US-ryan-high.onnx
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_carrusel import (  # noqa: E402
    buscar, cargar_fuente, render_slide,
)

W, H = 1080, 1920
PAD = 0.45          # silencio después de cada frase, en segundos
MIN_SLIDE = 2.2     # ningún plano baja de esto aunque la frase sea corta


def run(cmd, quiet=True):
    r = subprocess.run(cmd, capture_output=quiet, text=True)
    if r.returncode != 0:
        sys.stderr.write((r.stderr or "")[-1500:] + "\n")
        raise SystemExit(f"Falló: {' '.join(cmd[:5])} ...")
    return r


def narracion(slide):
    """Texto que se lee en voz alta. El titular trae saltos de línea para el
    diseño; para la voz hay que aplanarlos y asegurar que termine en punto."""
    tit = " ".join(slide["titulo"].split())
    sub = " ".join(slide.get("sub", "").split())
    tit = re.sub(r"\s+", " ", tit).strip()
    if tit and tit[-1] not in ".!?":
        tit += "."
    return f"{tit} {sub}".strip()


def dur_wav(ruta):
    import wave
    with wave.open(str(ruta)) as w:
        return w.getnframes() / w.getframerate()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="build_reel")
    p.add_argument("--voz", required=True, help="Ruta al modelo .onnx de Piper")
    p.add_argument("--fuentes", default="assets/fuentes")
    p.add_argument("--handle", default="@yourcoveragedesk")
    p.add_argument("--pieza", help="Forzar una pieza por id")
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
        # Al revés: el carrusel va p01→p12 y el Reel p12→p01, así nunca
        # coinciden en la misma semana.
        pieza = next((x for x in reversed(banco) if x["id"] not in hechas), None)
        if not pieza:
            raise SystemExit("BANCO_VACIO: no quedan piezas sin publicar como Reel.")

    fd = args.fuentes
    anton = buscar(f"{fd}/Anton-Regular.ttf", "Anton-Regular.ttf")
    dvs = buscar(f"{fd}/DejaVuSans.ttf", "DejaVuSans.ttf")
    dvb = buscar(f"{fd}/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf")
    # Tipos más grandes que en el carrusel: el Reel se ve en movimiento y de lejos.
    fuentes = (cargar_fuente(anton, 104), cargar_fuente(dvs, 42),
               cargar_fuente(dvb, 26), cargar_fuente(anton, 58))

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    tmp = out / "tmp"
    tmp.mkdir()

    slides = pieza["slides"]
    clips = []
    total_s = 0.0

    for i, s in enumerate(slides):
        # --- voz ---
        texto = narracion(s)
        wav = tmp / f"voz_{i:02d}.wav"
        r = subprocess.run(["python", "-m", "piper", "-m", args.voz, "-f", str(wav)],
                           input=texto, capture_output=True, text=True)
        if r.returncode != 0 or not wav.exists():
            sys.stderr.write((r.stderr or "")[-800:] + "\n")
            raise SystemExit(f"Piper falló en el slide {i + 1}.")
        dur = max(dur_wav(wav) + PAD, MIN_SLIDE)
        total_s += dur

        # --- imagen vertical, sin paginación ---
        img = render_slide(s, i, len(slides), pieza.get("badge", "COVERAGE 101"),
                           args.handle, fuentes, size=(W, H), paginar=False, base_ratio=0.72)
        png = tmp / f"card_{i:02d}.png"
        img.save(png)

        # --- clip con zoom lento: da vida sin distraer del texto ---
        clip = tmp / f"clip_{i:02d}.mp4"
        fps = 30
        frames = int(dur * fps)
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

    # Portada: un frame del primer plano, ya con el gancho visible.
    run(["ffmpeg", "-y", "-i", str(reel), "-ss", "0.5", "-vframes", "1",
         "-q:v", "2", str(out / "portada.jpg")])

    caption = pieza["caption"] + "\n\n" + " ".join(pieza.get("hashtags", []))
    (out / "caption.txt").write_text(caption)
    (out / "pieza.json").write_text(json.dumps(
        {"id": pieza["id"], "tema": pieza["tema"], "duracion": round(total_s, 1)},
        indent=2, ensure_ascii=False))

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\nPieza: {pieza['id']} — {pieza['tema']}")
    print(f"{reel}  ({total_s:.1f}s)")
    if total_s < 15:
        print("AVISO: menos de 15s. Instagram lo admite, pero rinde peor.", file=sys.stderr)
    if total_s > 90:
        print("AVISO: más de 90s para un carrusel hablado es mucho.", file=sys.stderr)


if __name__ == "__main__":
    main()
