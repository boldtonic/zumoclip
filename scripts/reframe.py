"""Reencuadre a 9:16 con control manual. Sustituye a los scripts sueltos que
vivían en /tmp y se perdían al vaciarse.

    reframe.py TRAMO_FUENTE.mp4 SALIDA.mp4 [modo] ['{"0":0.36}']
    reframe.py TRAMO_FUENTE.mp4 --escenas

Modos:
  cut    corta a quien habla (SPEAKER_CUT). Para conversaciones donde los dos
         salen en el mismo plano.
  track  plano cerrado en todas las escenas. Para fuentes que alternan primeros
         planos con generales muy abiertos, donde el clasificador elegiría
         GENERAL y dejaría a la gente diminuta.

El cuarto argumento son los overrides de encuadre, un JSON por índice de escena
(los índices salen de `--escenas`). Fracciones del ancho y alto de la fuente:

  {"3": 0.54}                              plano fijo, centrado al 54% del ancho
  {"5": {"top": 0.16, "bottom": 0.54}}     pantalla dividida, dos regiones apiladas
  {"5": {"top": {"x": 0.16, "y": 0.42}, "bottom": {"x": 0.54, "y": 0.42}}}

Se le pasa el tramo de la fuente horizontal, no un clip ya reencuadrado.
"""
import os
# Raiz de la instalacion de OpenShorts. Se puede fijar con OPENSHORTS_HOME.
OPENSHORTS = os.environ.get("OPENSHORTS_HOME", os.path.expanduser("~/openshorts"))
# ffmpeg CON libass para quemar subtítulos. El de Homebrew normal no lo trae,
# así que se busca ffmpeg-full en las rutas de Homebrew. FFMPEG lo sobrescribe.
FFMPEG = os.environ.get("FFMPEG") or next(
    (p for p in ("/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg",
                 "/usr/local/opt/ffmpeg-full/bin/ffmpeg") if os.path.exists(p)),
    "ffmpeg")
import json
import sys

sys.path.insert(0, OPENSHORTS)
from dotenv import load_dotenv
load_dotenv()

SRC = sys.argv[1]

if len(sys.argv) > 2 and sys.argv[2] == "--escenas":
    import main as m
    scenes, fps = m.detect_scenes(SRC)
    fps = float(fps)
    for i, (a, b) in enumerate(scenes):
        print(f"{i}  {a.get_frames()/fps:7.2f} -> {b.get_frames()/fps:7.2f}")
    raise SystemExit

OUT = sys.argv[2]
MODO = sys.argv[3] if len(sys.argv) > 3 else "cut"
# Un número fija el plano; un dict {"top","bottom"} divide la pantalla en esa escena.
OV = ({int(k): (v if isinstance(v, dict) else float(v))
       for k, v in json.loads(sys.argv[4]).items()} if len(sys.argv) > 4 else None)

if MODO == "cut":
    # El picker automatico vuelve a encender SPLIT por diseno, asi que no basta
    # con las variables de entorno: hay que forzar los modulos.
    os.environ["SPLIT_LAYOUT"] = "1"
    os.environ["SPEAKER_SIGNAL"] = "1"
    os.environ["SPEAKER_CUT"] = "1"
    import active_speaker, split_layout
    active_speaker.ENABLED = True
    active_speaker.CUT_MODE = True
    split_layout.ENABLED = True
    forzar = None
else:
    os.environ["AUTO_LAYOUT"] = "0"
    os.environ["SPLIT_LAYOUT"] = "0"
    os.environ["SCREENCAST_LAYOUT"] = "0"
    forzar = "TRACK"

import main as m
m.render_clip(SRC, OUT, output_format="vertical",
              force_strategy=forzar, crop_overrides=OV)
print("OK", OUT)
