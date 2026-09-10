# PROCESO — cómo producir un reel

Unos 25 minutos por reel, la mayor parte esperando a la CPU.
Todos los comandos se lanzan desde `~/openshorts`.

---

## Requisitos del entorno

Ya están instalados. Si hay que rehacerlo en otra máquina:

```bash
brew install ffmpeg ffmpeg-full python@3.11 deno
cd ~/openshorts && python3.11 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

- **`deno` es obligatorio.** YouTube exige un runtime de JavaScript para que yt-dlp extraiga los formatos.
- **`ffmpeg-full` es obligatorio.** La fórmula `ffmpeg` de Homebrew viene **sin `libass`** y no puede quemar subtítulos: falla con `Error opening output files: Filter not found`. Homebrew además no la enlaza, así que se invoca por ruta completa:

```
$FFMPEG
```

La key de Gemini va en `~/openshorts/.env`. Ese fichero también trae los layouts encendidos (`SPLIT_LAYOUT`, `AUTO_LAYOUT`, `SCREENCAST_LAYOUT`) y **`AUTO_HOOK=0`**, que debe quedarse a cero.

---

## 1 · Localizar el momento

Los capítulos de YouTube son el mapa. Sacarlos así:

```bash
yt-dlp --no-config --skip-download --print "%(chapters)#j" URL
```

Elige un tramo de 5 a 15 minutos, **nunca el vídeo entero**: procesar dos horas es tiempo de CPU tirado y devuelve clips repetidos.

Cuidado con solapar tramos ya procesados — pasó una vez y devolvió los mismos clips.

## 2 · Descargar solo ese tramo

En 1080p. El 4K no aporta nada al vertical y multiplica el tiempo de proceso.

```bash
yt-dlp --no-config --download-sections "*INICIO-FIN" \
  -f "bv[height<=1080]+ba/b[height<=1080]" --merge-output-format mp4 \
  -o "~/media/fuentes/NOMBRE.%(ext)s" URL
```

`INICIO` y `FIN` en segundos. `--no-config` es importante: un `~/.config/yt-dlp/config` global puede redirigir las descargas a otra carpeta.

## 3 · Pasar el pipeline

```bash
cd ~/openshorts
./.venv/bin/python main.py -i ~/media/fuentes/NOMBRE.mp4 \
  -o ~/media/bruto/NOMBRE/
```

Transcribe con Whisper en local, Gemini elige los momentos, reencuadra a 9:16 siguiendo las caras y quema los subtítulos en inglés.

Tarda unos **13 minutos por cada 15 de fuente** en el M1. Al terminar imprime el coste real de Gemini.

Salida: `NOMBRE_clip_N.mp4` (limpio), `subtitled_*.mp4` (con subtítulos) y `NOMBRE_metadata.json` con la transcripción completa, los tiempos y el copy generado.

## 4 · Repasar los bordes — NO SALTAR

El paso que separa publicable de mediocre. Gemini acierta el tema y falla el corte.

```bash
cd ~/media/bruto/NOMBRE && python3 -c "
import json,glob
d=json.load(open(glob.glob('*_metadata.json')[0]))
w=[]
for s in d['transcript']['segments']:
    for x in s.get('words',[]): w.append((x['start'],x['word']))
line=''; t0=None
for a,x in w:
    if t0 is None: t0=a
    line+=x
    if len(line)>95: print(f'{t0:6.1f} |{line}'); line=''; t0=None
"
```

Con eso delante, comprueba de cada clip:
- ¿empieza a mitad de frase?
- ¿acaba a mitad de frase?
- ¿el remate entra dentro del corte, o se queda fuera?

Si el corte no cuadra, apunta el segundo exacto donde debería empezar y acabar.

**Para elegir el punto de corte limpio, mira el audio**, no solo los tiempos de Whisper (que van desfasados):

```bash
FF=$FFMPEG
$FF -nostdin -v error -ss INICIO -t 2.0 -i CLIP.mp4 -ac 1 -ar 16000 -f s16le -y /tmp/s.raw
python3 -c "
import struct,math
d=open('/tmp/s.raw','rb').read(); n=len(d)//2
s=struct.unpack(f'<{n}h',d); SR=16000; win=320
for i in range(0,n-win,win):
    seg=s[i:i+win]; rms=math.sqrt(sum(x*x for x in seg)/len(seg))
    print(f'{INICIO+i/SR:6.2f} {rms:7.0f} ' + '#'*int(rms/120))
"
```

El corte va en el valle de silencio, no en mitad de una palabra. Si no hay silencio (dos palabras pegadas), corta igual y mete un fundido de audio de 0,1 s.

## 5 · Traducir al español

```bash
./.venv/bin/python traducir.py METADATA.json IDX DURACION salida.json
```

- `IDX` es el índice del clip empezando en 0 (clip_1 → 0)
- `DURACION` en segundos, ya con el recorte del paso 4 aplicado

Para un rango arbitrario que no corresponde a ningún clip:

```bash
./.venv/bin/python traducir_rango.py METADATA.json INICIO FIN salida.json
```

**El script ya recorta cada segmento a las palabras audibles antes de traducir.** No lo cambies: traducir la frase entera de Whisper hace que se pierda texto por los extremos del clip.

Revisa el JSON antes de seguir. Se puede editar a mano — es solo texto, no cuesta nada y no hay que volver a llamar a la API. Quita fragmentos colgando ("Trabajé", "Y") y ajusta la traducción si hay una frase que merece una localización mejor que la literal.

## 6 · Quemar los subtítulos españoles

```bash
./.venv/bin/python subs_es.py salida.json CLIP_LIMPIO.mp4 DURACION FINAL.mp4
```

Usa el clip **limpio** (`NOMBRE_clip_N.mp4`), no el `subtitled_*`, o quedarán dos capas de subtítulos superpuestas.

Estilo: Anton en mayúsculas, palabra activa en amarillo, contorno negro. `max_chars=14` en español (12 en inglés) — más alto rompe la línea en dos a mitad de reproducción.

## 7 · La portada

```bash
./.venv/bin/python portada.py CLIP_LIMPIO.mp4 "Titular" portada.jpg "PALABRA" MAXSEG "Tag de serie" MINSEG
```

- `MAXSEG` limita el muestreo a la parte recortada del clip
- `"PALABRA"` se pinta en amarillo; déjalo vacío `""` para todo blanco
- `MINSEG` (opcional, séptimo) fija desde qué segundo muestrear
- **Siempre desde el clip limpio.** Si usas el que ya tiene subtítulos, el titular se solapa con ellos

Elige el mejor fotograma por tamaño de cara (MediaPipe) y nitidez (Laplaciano), oscurece la parte de abajo y quema el titular en Anton.

**El criterio de "cara grande" tiene un sesgo:** si el entrevistador está más cerca de la cámara que el invitado, gana él siempre y la portada sale con la persona equivocada. Pasó con Rosalía en SubwayTakes. La solución es acotar la ventana con `MINSEG`/`MAXSEG` a un segundo donde salga quien tiene que salir — mira antes qué hay:

```bash
FF=$FFMPEG
for t in 17 18 19 20 21; do $FF -nostdin -v error -ss $t -i CLIP.mp4 -frames:v 1 -vf scale=200:-1 /tmp/w_$t.jpg -y; done
$FF -nostdin -v error -i /tmp/w_17.jpg -i /tmp/w_18.jpg -i /tmp/w_19.jpg -i /tmp/w_20.jpg -i /tmp/w_21.jpg \
  -filter_complex hstack=inputs=5 -y /tmp/win.jpg
```

## 7b · Si el encuadre sigue a quien no habla

**El TRACK no sigue al hablante.** Elige una cara al arrancar la escena y se
queda con ella hasta el final. En una conversación a dos eso significa que
puedes ver al entrevistador el clip entero mientras habla el invitado.

Lo que sí corta a quien habla es **`SPEAKER_CUT`**, que en el `.env` está
comentado. Y no basta con las variables de entorno, porque el picker automático
vuelve a encender SPLIT por diseño — está escrito como aditivo a propósito. Hay
que forzar los módulos desde Python:

```python
# /tmp/cut_reframe.py
import os, sys
sys.path.insert(0,"$OPENSHORTS_HOME")
from dotenv import load_dotenv; load_dotenv()
os.environ["SPLIT_LAYOUT"]="1"; os.environ["SPEAKER_SIGNAL"]="1"; os.environ["SPEAKER_CUT"]="1"
import active_speaker, split_layout
active_speaker.ENABLED=True; active_speaker.CUT_MODE=True; split_layout.ENABLED=True
import main as m
m.render_clip(sys.argv[1], sys.argv[2], output_format="vertical")
```

```bash
./.venv/bin/python /tmp/cut_reframe.py TRAMO_FUENTE.mp4 SALIDA.mp4
```

Se le pasa el **tramo de la fuente horizontal**, no el clip ya reencuadrado.
Unos 60 s de máquina por minuto de vídeo. Coste de API: 0.

Otras dos opciones desde la misma API, ninguna expuesta en el CLI:

- `m.render_clip(..., force_strategy='TRACK')` — plano cerrado en todas las
  escenas, pero con el sesgo de arriba: puede clavarse en quien no habla.
- `m.render_clip(..., crop_overrides={idx: 0.72})` — fija a mano el centro del
  recorte de una escena, como fracción del ancho de la fuente. Es lo que hay
  que usar cuando quieres decir "del segundo 5 al 12 quiero a Rosalía".

**Apagar `SPLIT_LAYOUT` no sirve de nada por sí solo**, y apagar además
`AUTO_LAYOUT` deja GENERAL, que es peor: los dos encogidos sobre fondo
desenfocado.

## 7c · Forzar el encuadre de un tramo concreto

Cuando en la revisión sale "del segundo X al Y quiero a fulano", el flujo es este.

**1. Saca las escenas del tramo de fuente:**

```bash
./.venv/bin/python -c "
import sys; sys.path.insert(0,'$OPENSHORTS_HOME')
import main as m
scenes,fps=m.detect_scenes('TRAMO_FUENTE.mp4'); fps=float(fps)
for i,(a,b) in enumerate(scenes): print(i, round(a.get_frames()/fps,2), '->', round(b.get_frames()/fps,2))
"
```

Los tiempos son del **tramo de fuente**, no del clip final. Para pasar de uno a
otro: `t_fuente = t_clip + (inicio_del_clip - inicio_del_tramo)`.

**2. Localiza a la persona en el plano ancho.** Saca un fotograma del tramo y
mide a qué fracción del ancho está su cara:

```bash
FF=$FFMPEG
$FF -nostdin -v error -ss SEGUNDO -i TRAMO_FUENTE.mp4 -frames:v 1 -vf scale=480:-1 /tmp/f.jpg -y
```

**3. Reencuadra con el override**, indicando índice de escena y esa fracción:

```bash
./.venv/bin/python scripts/cut_reframe_ov.py TRAMO_FUENTE.mp4 SALIDA.mp4 '{"5":0.54}'
```

Escenas no nombradas conservan el encuadre automático, así que corregir un plano
malo no estropea los que estaban bien. La unidad mínima es **la escena entera**:
no se puede forzar medio plano. Si el tramo que quieres cae a caballo de dos
escenas, o fuerzas las dos o te conformas con la que más se acerque.

## 8 · Copy

Estructura que funciona:

> **La cita primero. El contexto después. Ninguna pregunta al final.**

Lo que NO hacer: empezar por "Tom Holland dijo que...", cerrar con "¿qué opinas?", o usar lenguaje de nota de prensa ("estas curiosas declaraciones").

Ejemplo bueno:

> Comía sano. Entrenaba dos horas al día. Y no dormía.
> Tardó un anillo en descubrir por qué.

## 9 · Archivar la serie

Cada entrevista es una serie, con su carpeta. Vídeo y portada comparten nombre,
numerados desde 1 dentro de la serie.

```bash
S=./series/03_invitado_programa
mkdir -p "$S"
cp FINAL.mp4  "$S"/1_nombre.mp4
cp portada.jpg "$S"/1_nombre.jpg
```

Escribe un `SERIE.md` dentro copiando la estructura de los existentes: fuente,
tramos procesados, tabla de clips, copy de cada post y notas de producción.

Y actualiza `ESTADO.md`.

---

## Fallos conocidos

| Síntoma | Causa | Solución |
|---|---|---|
| `Filter not found` al quemar subtítulos | El `ffmpeg` de Homebrew no trae `libass` | Usar `ffmpeg-full` por ruta completa |
| El subtítulo salta a dos líneas a media reproducción | `max_chars` cuenta caracteres, no ancho renderizado | 12 en inglés, 14 en español |
| Palabras españolas pegadas sin espacios | Whisper entrega cada palabra con espacio delante; `split()` lo quita | Ya resuelto en `subs_es.py`, no tocar |
| Falta texto al principio o al final del clip | Se tradujo la frase completa de Whisper | Ya resuelto en `traducir.py`, no tocar |
| ffmpeg se come el bucle del shell | Consume stdin | Añadir `-nostdin` |
| yt-dlp descarga en `~/Downloads` | Config global de yt-dlp | Añadir `--no-config` |
| Los argumentos de un bucle llegan pegados | zsh no separa palabras como bash | Usar Python para los bucles |
| El encuadre sigue al que NO habla | TRACK fija una cara al empezar la escena y no la suelta | `SPEAKER_CUT`, ver paso 7b |
| La portada saca al entrevistador | Elige por tamaño de cara y él está más cerca | Acotar la ventana con `MINSEG`/`MAXSEG` |
| `SPLIT_LAYOUT=0` no apaga el split | El picker automático lo reactiva, es aditivo por diseño | Forzar los módulos desde Python, ver 7b |
| El SPLIT no se activa | La fuente está rodada a plano y contraplano | No es un fallo. Sin los dos en el mismo plano, no hay nada que apilar |
| Salen subtítulos amarillos que no son nuestros | La fuente los lleva quemados; en SPLIT se duplican | Empezar el clip donde no aparecen, o recortar la banda inferior |
| GENERAL encoge a los dos sobre fondo desenfocado | El clasificador manda ahí los planos muy abiertos | `force_strategy='TRACK'`, ver 7b |
