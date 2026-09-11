import os
# Raiz de la instalacion de OpenShorts. Se puede fijar con OPENSHORTS_HOME.
OPENSHORTS = os.environ.get("OPENSHORTS_HOME", os.path.expanduser("~/openshorts"))
# ffmpeg CON libass para quemar subtítulos. El de Homebrew normal no lo trae,
# así que se busca ffmpeg-full en las rutas de Homebrew. FFMPEG lo sobrescribe.
FFMPEG = os.environ.get("FFMPEG") or next(
    (p for p in ("/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg",
                 "/usr/local/opt/ffmpeg-full/bin/ffmpeg") if os.path.exists(p)),
    "ffmpeg")
import json, os, sys, glob
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel
from typing import List
load_dotenv(os.path.join(OPENSHORTS, '.env'))
META, ST, EN, OUT = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
meta=json.load(open(META))
segs=[]
for g in meta['transcript']['segments']:
    if g['end']<=ST or g['start']>=EN: continue
    ws=[w for w in g.get('words',[]) if w['end']>ST and w['start']<EN]
    if not ws: continue
    txt=''.join(w['word'] for w in ws).strip()
    if txt: segs.append({"start":max(ST,ws[0]['start']),"end":min(EN,ws[-1]['end']),"t":txt})
class S(BaseModel):
    i:int; es:str
class R(BaseModel):
    segs:List[S]
c=genai.Client(api_key=os.environ['GEMINI_API_KEY'])
r=c.models.generate_content(model="gemini-3.1-flash-lite",
  contents=("Traduce al ESPAÑOL DE ESPAÑA cada segmento. Subtítulos de short vertical: natural, hablado, conciso. "
   "Cada segmento puede empezar/acabar a mitad de frase porque es un recorte: traduce EXACTAMENTE ese fragmento. "
   "Devuelve el mismo índice i.\n\n"+json.dumps([{"i":i,"t":g['t']} for i,g in enumerate(segs)],ensure_ascii=False)),
  config={"response_mime_type":"application/json","response_schema":R})
out={x.i:x.es for x in r.parsed.segs}
u=r.usage_metadata
print(f"coste: ${(u.prompt_token_count*0.25+u.candidates_token_count*1.5)/1e6:.6f}")
for i,g in enumerate(segs):
    print(f"  EN: {g['t'][:70]}"); print(f"  ES: {out.get(i,'')[:70]}")
json.dump({"start":ST,"end":EN,"segs":[{"start":g['start'],"end":g['end'],"es":out.get(i,'')} for i,g in enumerate(segs)]},
  open(OUT,'w'),ensure_ascii=False,indent=1)
