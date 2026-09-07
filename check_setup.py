#!/usr/bin/env python3
"""Valida credenciales ANTES de publicar.

Existe porque casi todos los fallos de este pipeline son de configuración —
token caducado, cuenta que no es profesional, llave mal pegada — y salen a la
luz en la primera publicación real, cuando ya se perdió el post del día.

Uso:  python scripts/check_setup.py
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

IG = "https://graph.instagram.com/v23.0"


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



def get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def check(nombre, fn):
    try:
        return {"check": nombre, "ok": True, "detalle": fn()}
    except urllib.error.HTTPError as e:
        return {"check": nombre, "ok": False, "detalle": f"HTTP {e.code}: {e.read().decode()[:200]}"}
    except Exception as e:  # noqa: BLE001
        return {"check": nombre, "ok": False, "detalle": str(e)[:200]}


def main():
    res = []
    token = os.environ.get("META_ACCESS_TOKEN")
    ig_id = os.environ.get("IG_USER_ID")

    if token and ig_id:
        def cuenta():
            q = urllib.parse.urlencode({
                "fields": "username,account_type,media_count",
                "access_token": token,
            })
            d = get(f"{IG}/{ig_id}?{q}")
            tipo = d.get("account_type", "?")
            if tipo not in ("BUSINESS", "MEDIA_CREATOR", "CREATOR"):
                raise RuntimeError(f"la cuenta es '{tipo}'; hace falta profesional")
            return f"@{d.get('username')} ({tipo}, {d.get('media_count', 0)} posts)"
        res.append(check("Cuenta de Instagram", cuenta))
    else:
        faltan = [n for n, v in (("META_ACCESS_TOKEN", token), ("IG_USER_ID", ig_id)) if not v]
        res.append({"check": "Instagram", "ok": False, "detalle": "Faltan: " + ", ".join(faltan)})

    def pexels():
        k = os.environ["PEXELS_API_KEY"]
        d = get("https://api.pexels.com/v1/search?query=test&per_page=1", {"Authorization": k})
        return f"{d.get('total_results', 0)} resultados de prueba"

    def pixabay():
        k = os.environ["PIXABAY_API_KEY"]
        d = get(f"https://pixabay.com/api/?key={urllib.parse.quote(k)}&q=test&per_page=3")
        return f"{d.get('totalHits', 0)} resultados de prueba"

    if os.environ.get("PEXELS_API_KEY"):
        res.append(check("Pexels", pexels))
    if os.environ.get("PIXABAY_API_KEY"):
        res.append(check("Pixabay", pixabay))
    if not (os.environ.get("PEXELS_API_KEY") or os.environ.get("PIXABAY_API_KEY")):
        res.append({"check": "Medios de stock", "ok": True,
                    "detalle": "sin llaves; los carruseles no las necesitan todavía"})

    # Banco de contenido
    def banco():
        b = json.load(open(buscar("contenido/banco.json", "banco.json")))["piezas"]
        e = json.load(open(buscar("contenido/estado.json", "estado.json"))).get("publicadas", [])
        quedan = [p for p in b if p["id"] not in e]
        if not quedan:
            raise RuntimeError("no quedan piezas sin publicar; añade más a banco.json")
        return f"{len(quedan)} piezas pendientes de {len(b)}; siguiente: {quedan[0]['id']}"
    res.append(check("Banco de contenido", banco))

    for r in res:
        print(f"{'OK   ' if r['ok'] else 'FALLO'}  {r['check']}: {r['detalle']}")
    fallos = [r for r in res if not r["ok"]]
    print(f"\n{len(res) - len(fallos)}/{len(res)} correctos.")
    if fallos:
        print("Arregla lo anterior antes de programar publicaciones.", file=sys.stderr)
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
