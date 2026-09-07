# Your Coverage Desk — robot de publicación

Publica un carrusel educativo en Instagram cada día laborable, solo, desde
GitHub. Tú no tienes que abrir nada.

---

## Puesta en marcha (una sola vez, ~10 minutos)

### 1. Sube este repositorio a GitHub

Crea un repositorio **privado** llamado `yourcoveragedesk` y sube todos estos
archivos. Privado es a propósito: aquí no hay secretos, pero tampoco hace falta
que nadie vea el banco de contenido antes que tu audiencia.

### 2. Pega los dos secretos

En el repositorio: **Settings → Secrets and variables → Actions → New repository secret**.

| Nombre del secreto | Qué es | De dónde sale |
|---|---|---|
| `IG_USER_ID` | el número largo de tu cuenta | paso 6 de la guía de arranque |
| `META_ACCESS_TOKEN` | el token de Instagram | paso 6 de la guía de arranque |

Escríbelos **exactamente así**, en mayúsculas y con guion bajo. Si te equivocas
en una letra, el robot no los encuentra.

> Los de Pexels y Pixabay todavía no hacen falta. Los carruseles se dibujan con
> código, sin fotos de stock. Los necesitarás cuando pasemos a Reels.

### 3. Pruébalo a mano antes de dejarlo solo

**Actions → Publicar carrusel → Run workflow**.

Eso publica la primera pieza ahora mismo. Míralo en Instagram antes de confiar
en el horario automático.

### 4. Ya está

A partir de ahí publica solo, de **lunes a viernes a las 11:23 de la mañana**
hora del Este.

---

## Qué hace, en orden

1. Comprueba que las credenciales sirven. Si algo falla, se para aquí y te avisa.
2. Toma la siguiente pieza sin publicar de `contenido/banco.json`.
3. Dibuja los 5 slides en 1080×1350 con la identidad de la marca.
4. Los sube a una Release del repositorio, porque Instagram exige que las
   imágenes estén en una dirección pública.
5. Los publica como carrusel, con su texto y sus hashtags.
6. Marca la pieza como publicada — solo si todo lo anterior salió bien.

---

## Cómo añadir más contenido

Todo vive en **`contenido/banco.json`**. Copia un bloque entero, cámbiale el
`id` y reescribe el texto. El robot va en orden y nunca repite.

Cada pieza tiene:

- `id` — único, no lo repitas
- `badge` — la etiqueta de arriba a la izquierda: `COVERAGE 101`, `COMMERCIAL` o `THE DESK`
- `slides` — de 2 a 10. Cada uno con `titulo` (pocas palabras, va en grande),
  `sub` (una o dos frases) y opcionalmente `dato` (lo que va en el círculo ámbar)
- `caption` y `hashtags`

**Regla de oro de los slides:** el `titulo` es un cartel, no una frase. Si no se
lee de un vistazo en el móvil, es demasiado largo. Usa `\n` para forzar dónde
corta la línea.

### Cuando se acaben las piezas

El robot se para y te avisa con `BANCO_VACIO`. No publica nada repetido ni
inventa contenido. Añade piezas y sigue solo.

---

## Mantenimiento: lo único que tienes que vigilar

**El token caduca cada 60 días.** Los lunes el robot lo renueva solo y te
imprime el nuevo en el registro del job. Cuando eso pase:

1. Entra al job **refrescar-token** en Actions.
2. Copia el token nuevo del registro.
3. Actualiza el secreto `META_ACCESS_TOKEN`.

Si ese job sale en rojo, **atiéndelo ese mismo día**. Es el fallo que mata estos
sistemas en silencio: dejan de publicar y nadie se entera hasta semanas después.

---

## Si algo se rompe

| Lo que ves | Qué pasa |
|---|---|
| `Falta la variable IG_USER_ID` | El secreto no está creado o está mal escrito |
| `la cuenta es 'PERSONAL'` | La cuenta de Instagram no está en modo profesional |
| `HTTP 400` al crear el contenedor | Casi siempre la URL de la imagen no es pública. Comprueba que la Release se creó |
| `BANCO_VACIO` | Se acabaron las piezas. Añade más a `banco.json` |
| El job de token en rojo | Renueva el token a mano ese día, desde el panel de Meta |

---

## Probar en tu computadora (opcional)

```bash
pip install Pillow
python scripts/build_carrusel.py --out build
```

Eso dibuja los slides en `build/` sin publicar nada. Útil para ver cómo queda
una pieza nueva antes de que salga.
