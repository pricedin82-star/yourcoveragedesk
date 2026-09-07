#!/usr/bin/env python3
"""Publica un carrusel en Instagram con la API de Instagram Login.

Ojo con el detalle que rompe la mayoría de los intentos: esta vía usa
graph.instagram.com, NO graph.facebook.com. Si copias ejemplos de internet que
usen graph.facebook.com, fallarán con un error poco descriptivo.

Uso:
    python scripts/publish_ig.py --urls url1 url2 url3 --caption-file build/caption.txt
    python scripts/publish_ig.py --refrescar-token

Variables de entorno:
    IG_USER_ID          número largo de tu cuenta profesional
    META_ACCESS_TOKEN   token de larga duración (60 días)
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://graph.instagram.com/v23.0"
REFRESH = "https://graph.instagram.com/refresh_access_token"


def env(nombre):
    v = os.environ.get(nombre)
    if not v:
        raise SystemExit(f"Falta la variable {nombre}. Corre scripts/check_setup.py.")
    return v


def http(url, data=None, intentos=4):
    """Con backoff: Meta devuelve 429 y 5xx transitorios con cierta frecuencia,
    y un fallo aquí pierde el post del día."""
    body = urllib.parse.urlencode(data).encode() if data else None
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, data=body)
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            detalle = e.read().decode()[:600]
            if e.code in (429, 500, 502, 503, 504) and i < intentos - 1:
                espera = 2 ** (i + 2)
                print(f"  HTTP {e.code}; reintento en {espera}s", file=sys.stderr)
                time.sleep(espera)
                continue
            raise SystemExit(f"HTTP {e.code} en {url.split('?')[0]}\n{detalle}")
        except urllib.error.URLError as e:
            if i < intentos - 1:
                time.sleep(2 ** (i + 2))
                continue
            raise SystemExit(f"Error de red: {e}")
    raise SystemExit("Sin intentos restantes")


def esperar_listo(creation_id, token, etiqueta):
    """Publicar antes de FINISHED falla con un error confuso. Sondear es obligatorio."""
    for intento in range(40):
        q = urllib.parse.urlencode({"fields": "status_code,status", "access_token": token})
        est = http(f"{BASE}/{creation_id}?{q}")
        code = est.get("status_code")
        if code == "FINISHED":
            return
        if code == "ERROR":
            raise SystemExit(f"Instagram rechazó {etiqueta}: {est.get('status')}")
        time.sleep(5 if intento < 12 else 10)
    raise SystemExit(f"{etiqueta} no terminó de procesarse en ~6 min.")


def publicar_carrusel(urls, caption):
    ig, token = env("IG_USER_ID"), env("META_ACCESS_TOKEN")
    if not 2 <= len(urls) <= 10:
        raise SystemExit(f"Un carrusel de Instagram lleva entre 2 y 10 imágenes; me pasaste {len(urls)}.")

    hijos = []
    for i, url in enumerate(urls, 1):
        r = http(f"{BASE}/{ig}/media", {
            "image_url": url,
            "is_carousel_item": "true",
            "access_token": token,
        })
        cid = r["id"]
        esperar_listo(cid, token, f"slide {i}")
        hijos.append(cid)
        print(f"  slide {i}/{len(urls)} listo")

    r = http(f"{BASE}/{ig}/media", {
        "media_type": "CAROUSEL",
        "children": ",".join(hijos),
        "caption": caption,
        "access_token": token,
    })
    contenedor = r["id"]
    esperar_listo(contenedor, token, "el carrusel")

    pub = http(f"{BASE}/{ig}/media_publish", {
        "creation_id": contenedor,
        "access_token": token,
    })
    print(f"\nPUBLICADO — id {pub.get('id')}")
    return pub.get("id", "")


def refrescar_token():
    """Los tokens duran 60 días. Sin esto, el sistema muere en silencio a los dos
    meses. Falla en rojo a propósito para que GitHub avise."""
    token = env("META_ACCESS_TOKEN")
    q = urllib.parse.urlencode({"grant_type": "ig_refresh_token", "access_token": token})
    r = http(f"{REFRESH}?{q}")
    nuevo = r.get("access_token", "")
    dias = int(r.get("expires_in", 0)) // 86400
    if not nuevo:
        raise SystemExit(f"El refresco no devolvió token: {r}")
    print(f"Token renovado. Vence en {dias} días.")
    print(f"Empieza por: {nuevo[:12]}...  (longitud {len(nuevo)})")
    print("\nACCIÓN: copia el token completo del log cifrado y actualiza el secreto")
    print("META_ACCESS_TOKEN del repositorio. El valor completo NO se imprime por seguridad.")
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--urls", nargs="+", help="URLs públicas de los slides, en orden")
    p.add_argument("--caption-file", default="build/caption.txt")
    p.add_argument("--refrescar-token", action="store_true")
    args = p.parse_args()

    if args.refrescar_token:
        return refrescar_token()
    if not args.urls:
        p.error("indica --urls o --refrescar-token")

    caption = ""
    if os.path.exists(args.caption_file):
        caption = open(args.caption_file).read().strip()
    if len(caption) > 2200:
        print("AVISO: caption recortado a 2200 caracteres.", file=sys.stderr)
        caption = caption[:2200]

    publicar_carrusel(args.urls, caption)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
