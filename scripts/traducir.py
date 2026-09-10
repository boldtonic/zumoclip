import os
# Raiz de la instalacion de OpenShorts. Se puede fijar con OPENSHORTS_HOME.
OPENSHORTS = os.environ.get("OPENSHORTS_HOME", os.path.expanduser("~/openshorts"))
# ffmpeg CON libass. El de Homebrew normal no lo trae: usa ffmpeg-full.
FFMPEG = os.environ.get("FFMPEG", "ffmpeg")
import json, os, sys
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel
from typing import List

load_dotenv(os.path.join(OPENSHORTS, '.env'))
META=sys.argv[1]
IDX=int(sys.argv[2]); DUR=float(sys.argv[3]); OUT=sys.argv[4]

meta=json.load(open(META))
s=meta['shorts'][IDX]; st, en = s['start'], s['start']+DUR

# Recorta cada segmento a las palabras REALMENTE audibles dentro del clip.
segs=[]
for g in meta['transcript']['segments']:
    if g['end']<=st or g['start']>=en: continue
    ws=[w for w in g.get('words',[]) if w['end']>st and w['start']<en]
    if not ws: continue
    txt=''.join(w['word'] for w in ws).strip()
    if not txt: continue
    segs.append({"start":max(st,ws[0]['start']), "end":min(en,ws[-1]['end']), "t":txt})

src=[{"i":i,"t":g['t']} for i,g in enumerate(segs)]
print(f"{len(segs)} segmentos (recortados al clip)")

class Seg(BaseModel):
    i:int; es:str
class R(BaseModel):
    segs:List[Seg]

client=genai.Client(api_key=os.environ['GEMINI_API_KEY'])
prompt=("Traduce al ESPAÑOL DE ESPAÑA cada segmento de esta transcripción de podcast. "
 "Es para subtítulos de un short vertical: natural, hablado, conciso.\n"
 "IMPORTANTE: cada segmento puede empezar o acabar a mitad de frase porque es un recorte. "
 "Traduce EXACTAMENTE lo que dice ese fragmento, sin completar ni recortar la idea. "
 "Si el fragmento está incompleto, la traducción también debe estarlo.\n"
 "Devuelve el mismo índice i.\n\n" + json.dumps(src, ensure_ascii=False))
r=client.models.generate_content(model="gemini-3.1-flash-lite", contents=prompt,
    config={"response_mime_type":"application/json","response_schema":R})
out={x.i:x.es for x in r.parsed.segs}
u=r.usage_metadata
print(f"coste: ${(u.prompt_token_count*0.25 + u.candidates_token_count*1.5)/1e6:.6f}")
for i,g in enumerate(segs):
    print(f"  EN: {g['t'][:62]}")
    print(f"  ES: {out.get(i,'')[:62]}")
json.dump({"start":st,"end":en,
  "segs":[{"start":g['start'],"end":g['end'],"es":out.get(i,'')} for i,g in enumerate(segs)]},
  open(OUT,'w'), ensure_ascii=False, indent=1)
