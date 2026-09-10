"""Variante de portada para TikTok: la misma imagen, con la etiqueta de serie
repetida justo encima del titular.

    portada_tiktok.py PORTADA.jpg SALIDA.jpg "Tag de serie"

TikTok recorta la portada por arriba en la cuadrícula del perfil, así que la
etiqueta a 92 px se pierde. Aquí se detecta dónde empieza el titular por el
color exacto del texto —blanco puro y amarillo puro, que solo salen de lo que
pintamos nosotros— y se coloca una segunda etiqueta encima. La de arriba se
deja: cae fuera del recorte y quitarla obligaría a reconstruir el fondo.
"""
import os
# Raiz de la instalacion de OpenShorts. Se puede fijar con OPENSHORTS_HOME.
OPENSHORTS = os.environ.get("OPENSHORTS_HOME", os.path.expanduser("~/openshorts"))
# ffmpeg CON libass. El de Homebrew normal no lo trae: usa ffmpeg-full.
FFMPEG = os.environ.get("FFMPEG", "ffmpeg")
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

SRC, OUT, TAG = sys.argv[1], sys.argv[2], sys.argv[3]
ANTON=os.path.join(OPENSHORTS, 'fonts', 'Anton-Regular.ttf')

img=Image.open(SRC).convert('RGB')
W,H=img.size
a=np.asarray(img)

# blanco puro del titular o amarillo puro de la palabra destacada
texto=((a[:,:,0]>250)&(a[:,:,1]>250)&(a[:,:,2]>250)) | \
      ((a[:,:,0]>250)&(a[:,:,1]>215)&(a[:,:,1]<245)&(a[:,:,2]<40))

# solo la mitad inferior: arriba está la etiqueta vieja
mitad=int(H*0.45)
filas=np.where(texto[mitad:].sum(axis=1) > 12)[0]
if len(filas)==0: raise SystemExit(f"no se encontro el titular en {SRC}")
top=mitad+int(filas[0])

d=ImageDraw.Draw(img)
ft=ImageFont.truetype(ANTON, 40)
tw=d.textlength(TAG.upper(), font=ft)
by0=max(0, top-110)
bx0=(W-tw)//2-26
d.rounded_rectangle([bx0,by0,bx0+tw+52,by0+62], radius=8, fill=(255,212,0))
d.text(((W-tw)//2, by0+9), TAG.upper(), font=ft, fill=(0,0,0))
img.save(OUT, quality=95)
print(f"OK {OUT} (titular en y={top}, etiqueta en y={by0})")
