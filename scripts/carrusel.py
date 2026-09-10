"""Diapositivas de carrusel 1080x1350 (4:5): fotograma de un segundo concreto
del clip + la frase que se dice en ese momento, en el mismo lenguaje visual
que las portadas.

    carrusel.py CLIP_LIMPIO.mp4 SALIDA_DIR "Tag de serie" SEG:Texto[:PALABRA[:ZOOM[:X]]] ...

El clip es 9:16; se recorta a 4:5 centrado en la cara si se encuentra, y si no
por el centro geométrico. Cada argumento extra es una diapositiva.
"""
import os
# Raiz de la instalacion de OpenShorts. Se puede fijar con OPENSHORTS_HOME.
OPENSHORTS = os.environ.get("OPENSHORTS_HOME", os.path.expanduser("~/openshorts"))
# ffmpeg CON libass. El de Homebrew normal no lo trae: usa ffmpeg-full.
FFMPEG = os.environ.get("FFMPEG", "ffmpeg")
import sys, os
sys.path.insert(0, OPENSHORTS)
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont

VID, OUTDIR, TAG = sys.argv[1], sys.argv[2], sys.argv[3]
SLIDES = sys.argv[4:]
ANTON=os.path.join(OPENSHORTS, 'fonts', 'Anton-Regular.ttf')
W,H = 1080,1350

os.makedirs(OUTDIR, exist_ok=True)
cap=cv2.VideoCapture(VID)
fps=cap.get(cv2.CAP_PROP_FPS) or 25
import mediapipe as mp
_fd=mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)


def frame_at(seg):
    """Fotograma más nítido en una ventana de 0,4 s alrededor de `seg`.

    Un solo fotograma sale movido con demasiada frecuencia: la gente gesticula
    y habla, y el que cae justo en el segundo pedido puede ser el peor de los
    diez de alrededor."""
    best=(None,-1)
    for t in np.linspace(max(0,seg-0.2), seg+0.2, 7):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(t*fps))
        ok,fr=cap.read()
        if not ok: continue
        sharp=cv2.Laplacian(cv2.cvtColor(fr,cv2.COLOR_BGR2GRAY),cv2.CV_64F).var()
        if sharp>best[1]: best=(fr,sharp)
    return best[0]


def recorte_45(fr, zoom=1.0, xf=None):
    """9:16 -> 4:5, con la ventana centrada en la cara cuando la hay.

    `zoom` > 1 estrecha la ventana sobre la cara. Sirve para los planos muy
    abiertos, donde la ventana a ancho completo deja a la gente diminuta.
    `xf` fija el centro horizontal como fracción del ancho: hace falta cuando
    hay dos caras y la mayor no es la que quieres, que en una entrevista es lo
    normal — el entrevistador suele estar más cerca de la cámara."""
    fh,fw=fr.shape[:2]
    cw=int(fw/zoom); ch=int(cw*H/W)
    if ch>fh: ch=fh; cw=int(ch*W/H)
    res=_fd.process(cv2.cvtColor(fr,cv2.COLOR_BGR2RGB))
    cx,cy=fw//2,fh//2
    if res.detections:
        b=max(res.detections,key=lambda d:d.location_data.relative_bounding_box.height)
        rb=b.location_data.relative_bounding_box
        cx=int((rb.xmin+rb.width/2)*fw)
        # la cara en el tercio superior: deja sitio abajo para el texto
        cy=int((rb.ymin+rb.height/2)*fh + ch*0.16)
    if xf is not None: cx=int(xf*fw)
    x0=max(0,min(fw-cw, cx-cw//2))
    y0=max(0,min(fh-ch, cy-ch//2))
    return cv2.resize(fr[y0:y0+ch, x0:x0+cw], (W,H), interpolation=cv2.INTER_LANCZOS4)


def render(fr, texto, dest, out, zoom=1.0, xf=None):
    img=Image.fromarray(cv2.cvtColor(recorte_45(fr,zoom,xf),cv2.COLOR_BGR2RGB)).convert('RGB')

    grad=Image.new('L',(1,H))
    for y in range(H):
        t=max(0.0,(y-H*0.42)/(H*0.58))
        grad.putpixel((0,y), int(200*t**1.4))
    img=Image.composite(Image.new('RGB',(W,H),(0,0,0)), img, grad.resize((W,H)))

    d=ImageDraw.Draw(img); MARGIN=70; maxw=W-2*MARGIN
    palabras=texto.upper().split()
    for size in range(120,44,-4):
        f=ImageFont.truetype(ANTON,size)
        lineas=[]; cur=''
        for p in palabras:
            t=(cur+' '+p).strip()
            if d.textlength(t,font=f)<=maxw: cur=t
            else:
                if cur: lineas.append(cur)
                cur=p
        if cur: lineas.append(cur)
        if len(lineas)<=4 and all(d.textlength(l,font=f)<=maxw for l in lineas): break

    # anclado abajo: con 3 o 4 lineas, centrar en 0.80H metia el texto
    # encima de la marca
    lh=int(size*1.12); y=H-160-lh*len(lineas)
    for linea in lineas:
        x=(W-d.textlength(linea,font=f))//2
        for dx in range(-7,8,2):
            for dy in range(-7,8,2):
                d.text((x+dx,y+dy),linea,font=f,fill=(0,0,0))
        if dest and dest.upper() in linea:
            cx=x
            for w in linea.split(' '):
                col=(255,229,0) if w.strip('.,:"¿?¡!')==dest.upper() else (255,255,255)
                d.text((cx,y),w,font=f,fill=col); cx+=d.textlength(w+' ',font=f)
        else:
            d.text((x,y),linea,font=f,fill=(255,255,255))
        y+=lh

    if TAG:
        ft=ImageFont.truetype(ANTON,38)
        tw=d.textlength(TAG.upper(),font=ft)
        bx0,by0=(W-tw)//2-24, 72
        d.rounded_rectangle([bx0,by0,bx0+tw+48,by0+58], radius=8, fill=(255,212,0))
        d.text(((W-tw)//2, by0+8), TAG.upper(), font=ft, fill=(0,0,0))
    fm=ImageFont.truetype(ANTON,32)
    mw=d.textlength("@zumoclip",font=fm)
    d.text(((W-mw)//2, H-92), "@zumoclip", font=fm, fill=(255,255,255))
    img.save(out,quality=95)
    return size,len(lineas)


for i,spec in enumerate(SLIDES, start=1):
    partes=spec.split(':')
    seg=float(partes[0]); texto=partes[1]
    dest=partes[2] if len(partes)>2 else ""
    zoom=float(partes[3]) if len(partes)>3 and partes[3] else 1.0
    xf=float(partes[4]) if len(partes)>4 and partes[4] else None
    fr=frame_at(seg)
    if fr is None: raise SystemExit(f"no se pudo leer el segundo {seg}")
    out=os.path.join(OUTDIR, f"slide_{i}.jpg")
    size,n=render(fr, texto, dest, out, zoom, xf)
    print(f"OK {out} (s={seg}, {size}px, {n} lineas)")
cap.release()
