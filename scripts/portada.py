"""Portada vertical 1080x1920: mejor frame del clip + titular en Anton.
Reusa el criterio del repo para elegir frame: cara grande y nitida."""
import os
# Raiz de la instalacion de OpenShorts. Se puede fijar con OPENSHORTS_HOME.
OPENSHORTS = os.environ.get("OPENSHORTS_HOME", os.path.expanduser("~/openshorts"))
# ffmpeg CON libass. El de Homebrew normal no lo trae: usa ffmpeg-full.
FFMPEG = os.environ.get("FFMPEG", "ffmpeg")
import sys, os
sys.path.insert(0, OPENSHORTS)
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont

VID, TEXTO, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
DEST = sys.argv[4] if len(sys.argv)>4 else ""     # palabra a destacar en amarillo
MAXT = float(sys.argv[5]) if len(sys.argv)>5 else 0   # solo muestrear hasta este segundo
TAG  = sys.argv[6] if len(sys.argv)>6 else ""        # etiqueta de serie, arriba
MINT = float(sys.argv[7]) if len(sys.argv)>7 else 0   # no muestrear antes de este segundo
TAGPOS = sys.argv[8] if len(sys.argv)>8 else "arriba"  # "arriba" | "sobre" (encima del titular)
ANTON=os.path.join(OPENSHORTS, 'fonts', 'Anton-Regular.ttf')
W,H = 1080,1920

# --- 1. elegir el mejor frame: nitidez * cantidad de piel/cara ---
cap=cv2.VideoCapture(VID); total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
fps=cap.get(cv2.CAP_PROP_FPS) or 25
if MAXT: total=min(total,int(MAXT*fps))
lo, hi = (int(MINT*fps), total) if MINT else (total*0.1, total*0.9)
import mediapipe as mp
_fd=mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)
best=(None,-1)
for i in np.linspace(lo, hi, 24, dtype=int):
    cap.set(cv2.CAP_PROP_POS_FRAMES,int(i)); ok,fr=cap.read()
    if not ok: continue
    g=cv2.cvtColor(fr,cv2.COLOR_BGR2GRAY)
    sharp=cv2.Laplacian(g,cv2.CV_64F).var()
    res=_fd.process(cv2.cvtColor(fr,cv2.COLOR_BGR2RGB))
    area=0
    if res.detections:
        fh,fw=fr.shape[:2]
        for dd in res.detections:
            b=dd.location_data.relative_bounding_box
            area=max(area,(b.width*fw)*(b.height*fh))
    score=area*(1.0+min(sharp,500.0)/500.0)
    if score>best[1]: best=(fr,score)
cap.release()
if best[0] is None: raise SystemExit("no se pudo leer el video")

img=Image.fromarray(cv2.cvtColor(best[0],cv2.COLOR_BGR2RGB)).convert('RGB')
if img.size!=(W,H): img=img.resize((W,H), Image.LANCZOS)

# --- 2. oscurecer la mitad inferior para que el texto respire ---
grad=Image.new('L',(1,H))
for y in range(H):
    t=max(0.0,(y-H*0.45)/(H*0.55))
    grad.putpixel((0,y), int(190*t**1.4))
img=Image.composite(Image.new('RGB',(W,H),(0,0,0)), img, grad.resize((W,H)))

# --- 3. titular, ajustando tamano hasta que quepa en 3 lineas ---
d=ImageDraw.Draw(img); MARGIN=70; maxw=W-2*MARGIN
palabras=TEXTO.upper().split()
for size in range(140,54,-4):
    f=ImageFont.truetype(ANTON,size)
    lineas=[]; cur=''
    for p in palabras:
        t=(cur+' '+p).strip()
        if d.textlength(t,font=f)<=maxw: cur=t
        else:
            if cur: lineas.append(cur)
            cur=p
    if cur: lineas.append(cur)
    if len(lineas)<=3 and all(d.textlength(l,font=f)<=maxw for l in lineas): break

lh=int(size*1.12); total_h=lh*len(lineas); y=int(H*0.80)-total_h//2
for linea in lineas:
    x=(W-d.textlength(linea,font=f))//2
    for dx in range(-7,8,2):
        for dy in range(-7,8,2):
            d.text((x+dx,y+dy),linea,font=f,fill=(0,0,0))
    if DEST and DEST.upper() in linea:
        cx=x
        for w in linea.split(' '):
            col=(255,229,0) if w.strip('.,:"¿?¡!')==DEST.upper() else (255,255,255)
            d.text((cx,y),w,font=f,fill=col)
            cx+=d.textlength(w+' ',font=f)
    else:
        d.text((x,y),linea,font=f,fill=(255,255,255))
    y+=lh


# --- 4. etiqueta de serie y marca abajo ---
# TikTok recorta la portada por arriba en la cuadricula del perfil, asi que la
# etiqueta a 92px se pierde. Con TAGPOS="sobre" va pegada al titular, dentro de
# la zona que sobrevive al recorte.
if TAG:
    ft=ImageFont.truetype(ANTON,40)
    tw=d.textlength(TAG.upper(),font=ft)
    tag_y = (y - lh*len(lineas) - 110) if TAGPOS=="sobre" else 92
    bx0,by0=(W-tw)//2-26, tag_y
    d.rounded_rectangle([bx0,by0,bx0+tw+52,by0+62], radius=8, fill=(255,212,0))
    d.text(((W-tw)//2, by0+9), TAG.upper(), font=ft, fill=(0,0,0))
fm=ImageFont.truetype(ANTON,34)
mw=d.textlength("@zumoclip",font=fm)
d.text(((W-mw)//2, H-118), "@zumoclip", font=fm, fill=(255,255,255))

img.save(OUT,quality=95)
print("OK", OUT, f"({size}px, {len(lineas)} lineas)")
