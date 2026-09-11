import os
# Raiz de la instalacion de OpenShorts. Se puede fijar con OPENSHORTS_HOME.
OPENSHORTS = os.environ.get("OPENSHORTS_HOME", os.path.expanduser("~/openshorts"))
# ffmpeg CON libass para quemar subtítulos. El de Homebrew normal no lo trae,
# así que se busca ffmpeg-full en las rutas de Homebrew. FFMPEG lo sobrescribe.
FFMPEG = os.environ.get("FFMPEG") or next(
    (p for p in ("/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg",
                 "/usr/local/opt/ffmpeg-full/bin/ffmpeg") if os.path.exists(p)),
    "ffmpeg")
import json, os, sys, subprocess
sys.path.insert(0, OPENSHORTS)
import subtitles as S, layout_ranges as LR

ES=sys.argv[1]; SRC=sys.argv[2]; DUR=float(sys.argv[3]); OUT=sys.argv[4]
FF=FFMPEG
FD=os.path.join(OPENSHORTS, "fonts")

d=json.load(open(ES)); st=d['start']
# Reparte la duracion de cada frase entre sus palabras, proporcional a la longitud.
segments=[]
for g in d['segs']:
    txt=(g['es'] or '').strip()
    if not txt: continue
    ws=txt.split()
    total=sum(len(w) for w in ws) or 1
    dur=max(0.2, g['end']-g['start']); t=g['start']; words=[]
    for w in ws:
        wd=dur*len(w)/total
        words.append({"word":(" "+w),"start":round(t,3),"end":round(t+wd,3)})
        t+=wd
    segments.append({"start":g['start'],"end":g['end'],"text":txt,"words":words})

stl=dict(S.AUTO_CAPTION_STYLE); stl['max_chars']=14   # el español es más largo
ass=OUT.replace('.mp4','.ass')
S.generate_ass({"language":"es","segments":segments}, st, st+DUR, ass,
    max_chars=stl['max_chars'], max_duration=stl['max_duration'], alignment=stl['alignment'],
    fontsize=stl['font_size'], font_name=stl['font_name'], font_color=stl['font_color'],
    border_color=stl['border_color'], border_width=stl['border_width'],
    highlight_color=stl['highlight_color'], effect=stl['effect'],
    base_opacity=stl['base_opacity'], uppercase=stl['uppercase'],
    split_ranges=LR.split_ranges(LR.read(SRC)))
r=subprocess.run([FF,"-nostdin","-y","-loglevel","error","-i",SRC,"-t",str(DUR),
  "-vf",f"ass=filename='{ass}':fontsdir='{FD}'","-af",f"afade=t=out:st={DUR-0.08:.3f}:d=0.08",
  "-c:v","libx264","-preset","medium","-crf","18","-c:a","aac","-b:a","192k",
  "-movflags","+faststart",OUT],capture_output=True)
print(("OK  " if r.returncode==0 else "FALLO"), OUT, r.stderr.decode()[:150] if r.returncode else "")
