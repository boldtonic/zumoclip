---
name: zumoclip
description: Convierte entrevistas y podcasts largos en clips verticales 9:16 con subtítulos en español quemados que conservan la voz original, más portadas para Instagram y TikTok, carruseles 4:5 y el copy de cada post. Úsalo siempre que alguien quiera sacar clips, reels, shorts o tiktoks de una entrevista, un podcast o un vídeo de YouTube, subtitular en español una entrevista en inglés, o hacer portadas y carruseles de esos clips, aunque no mencione OpenShorts ni Zumoclip. También para peticiones en inglés como "clip this interview", "make shorts from this podcast" o "Spanish subtitles for this video".
---

# Zumoclip

Convierte una entrevista larga en clips verticales publicables: el momento bueno, cortado en su sitio, reencuadrado a 9:16, con subtítulos en español y la voz original. Se apoya en [OpenShorts](https://github.com/mutonby/openshorts), que hace el trabajo pesado (transcripción, selección de momentos, reencuadre). Este skill añade la traducción, las portadas, los carruseles y el control del encuadre, y sobre todo el criterio para que el clip salga publicable y no solo generado.

La raíz del plugin está dos carpetas por encima de este `SKILL.md`. Ahí están `install.sh`, `scripts/` y `PROCESO.md`, con los comandos detallados y la tabla de fallos conocidos: léelo cuando algo falle o necesites el detalle de un paso.

## 0 · Prepara el entorno

Comprueba primero, sin tocar nada:

```bash
bash <raíz>/install.sh --check
```

Si falta algo, `bash <raíz>/install.sh` lo instala. Descarga OpenShorts y unos 2 GB de dependencias, así que avisa antes de lanzarlo. Lo único que el usuario pone a mano es su `GEMINI_API_KEY` en `~/openshorts/.env`: dile dónde va, no le pidas que te la pegue en el chat.

Todos los comandos se lanzan desde `~/openshorts` (o `$OPENSHORTS_HOME`). Los scripts encuentran solos el `ffmpeg-full` de Homebrew, que es el que sabe quemar subtítulos.

## 1 · Elige bien la fuente

La fuente decide más que cualquier ajuste posterior. Antes de descargar nada, tres comprobaciones de diez segundos:

- **Vídeo real, no carátula.** Muchos podcasts están en YouTube como audio con una imagen fija. Descarga unos segundos de un tramo y mira un fotograma.
- **Sin marca de agua ni subtítulos quemados.** Un logo fijo en el fotograma invalida la fuente entera. Los subtítulos propios del programa se duplican al dividir la pantalla.
- **Audiencia.** Ordena por visualizaciones, no por relevancia: la misma persona puede tener una entrevista con 19 millones de vistas y otra con 500.000.

Lo que funciona: entrevistas **en inglés** de alguien **muy conocido para el público hispanohablante**, en formato **confesional** (Apple Music con Zane Lowe, SubwayTakes, podcasts largos de conversación). La confesión rinde mucho más que la anécdota, y los programas de gimmick (comer picante, preguntas rápidas) casi nunca dan un clip con sustancia. Un invitado entrevistado en español no sirve: no hay nada que subtitular.

```bash
yt-dlp --no-config --skip-download --print "%(view_count)s|%(duration)s|%(title)s|%(id)s" "ytsearch15:NOMBRE interview"
yt-dlp --no-config --skip-download --print "%(chapters)#j" URL
```

## 2 · Descarga tramos, no el vídeo entero

Usa los capítulos para elegir tramos de 10 a 15 minutos con lo personal —relaciones, crisis, cuerpo, fracaso, familia— y salta anuncios y promoción. `--no-config` evita que una configuración global de yt-dlp mande la descarga a otra carpeta.

```bash
yt-dlp --no-config -f "bv[height<=1080]+ba/b[height<=1080]" --merge-output-format mp4 -o "fuente.%(ext)s" URL
ffmpeg -nostdin -ss INICIO -t DURACION -i fuente.mp4 -c copy tramo.mp4
```

## 3 · Pasa el pipeline

```bash
AUTO_CAPTIONS=0 AUTO_HOOK=0 ./.venv/bin/python main.py -i tramo.mp4 -o bruto/tramo/
```

Sin subtítulos automáticos porque los quemamos nosotros en español, y sin hook porque el titular va en la portada. Tarda unos 13 minutos por cada 15 de fuente y cuesta alrededor de $0,00032 por minuto. Devuelve clips, un `*_metadata.json` con la transcripción palabra a palabra, y su propia propuesta de cortes.

## 4 · Revisa los bordes: el paso que no se salta

El modelo acierta el tema y falla el borde, en las dos direcciones: a veces se pasa 26 segundos, a veces corta justo antes del remate. Lee la transcripción palabra a palabra de cada clip y decide tú el inicio y el final:

- Que no empiece a mitad de frase ni con una muletilla del entrevistador.
- **Que la última palabra entre entera.** Busca el `end` de esa palabra en el metadata y deja 0,2–0,4 s de margen. Medio segundo es la diferencia entre "protegida" y "protegi".
- Entra ya en el remate. Si lo bueno dura 20 segundos, el clip dura 20. Funcionan dos velocidades: el golpe de 10 segundos y la construcción de 30–35. Lo que no funciona es un clip de 40 que son 20 buenos y 20 de preámbulo; muchas veces un clip largo son dos clips mejores.
- Prefiere lo que dice el invitado. Si un tramo es sobre todo el entrevistador, descártalo.

## 5 · Traduce

```bash
./.venv/bin/python traducir_rango.py bruto/tramo/tramo_metadata.json INICIO FIN es_clip.json
```

El script recorta cada frase de Whisper a las palabras que caen dentro del clip antes de traducir; si se traduce la frase entera se pierde texto por los extremos. El JSON resultante es texto plano y se corrige a mano sin coste. Revisa siempre:

- **Concordancia de género** con quien habla ("me gusto a mí misma", "estoy protegida").
- **Fragmentos colgando** al principio o al final ("Y", "Sí, yo"): quítalos.
- **No quites palabras que cargan el sentido** aunque suenen redundantes. "Si hubiera perdido la voz definitivamente" no es lo mismo sin "definitivamente".
- Las frases del entrevistador también se subtitulan. Si quitas una, queda un silencio que se nota.

## 6 · Reencuadra y quema los subtítulos

Pasa por el reencuadre el **tramo horizontal** alrededor del clip, no un clip ya vertical:

```bash
./.venv/bin/python reframe.py tramo_clip.mp4 --escenas                                         # índices y tiempos
./.venv/bin/python reframe.py tramo_clip.mp4 ref.mp4 cut                                       # corta a quien habla
./.venv/bin/python reframe.py tramo_clip.mp4 ref.mp4 track                                     # plano cerrado siempre
./.venv/bin/python reframe.py tramo_clip.mp4 ref.mp4 cut '{"5":0.54}'                          # escena 5 fijada
./.venv/bin/python reframe.py tramo_clip.mp4 ref.mp4 cut '{"5":{"top":0.16,"bottom":0.54}}'    # escena 5 dividida
```

- `cut` para conversaciones con los dos en plano. `track` para fuentes que alternan primeros planos con generales muy abiertos; si no, esos generales salen con la gente diminuta.
- El TRACK **no sigue a quien habla**: elige una cara al empezar la escena y se queda con ella. Saca fotogramas del resultado y comprueba quién sale mientras habla el invitado. Si sale quien no toca, fija esa escena con la fracción del ancho donde está su cara, o divide la pantalla si hacen falta los dos.
- La unidad mínima es la escena entera.

Después recorta el reencuadre al rango exacto y quema:

```bash
ffmpeg -nostdin -y -ss OFFSET -t DUR -i ref.mp4 -c:v libx264 -crf 18 -c:a aac clip_limpio.mp4
./.venv/bin/python subs_es.py es_clip.json clip_limpio.mp4 DUR final.mp4
```

`subs_es.py` asume que el clip empieza exactamente en el `start` del JSON: si cambias la entrada del clip, actualiza también ese `start`.

## 7 · Portadas

```bash
./.venv/bin/python portada.py clip_limpio.mp4 "TITULAR" portada.jpg "PALABRA" MAXSEG "Tag de serie" MINSEG
./.venv/bin/python portada_tiktok.py portada.jpg portada_tiktok.jpg "Tag de serie"
```

Siempre desde el clip **limpio**, o el titular se monta sobre los subtítulos. El detector elige la cara más grande y en una entrevista suele ser la del entrevistador: acota la ventana con `MINSEG`/`MAXSEG` a un momento en que salga el invitado. Titular en mayúsculas, con tildes, una palabra en amarillo. La versión de TikTok baja la etiqueta de serie porque TikTok recorta la parte de arriba en la cuadrícula del perfil.

## 8 · Carruseles

```bash
./.venv/bin/python carrusel.py clip_limpio.mp4 carrusel/ "Tag de serie" "SEG:Texto:PALABRA[:ZOOM[:X]]" ...
```

Cuatro diapositivas 4:5 con la estructura **portada → pregunta → giro → remate**, no tres titulares seguidos: un carrusel se lee como una conversación. Cada diapositiva es el fotograma del momento en que se dice su frase. `ZOOM` acerca en planos abiertos y `X` fija a quién enfocar cuando hay dos caras.

## 9 · Copy

```
"La cita, en una o dos líneas."

Contexto en una línea.

Nombre • Programa

#cinco #hashtags #como #máximo #marca
```

La cita va arriba porque Instagram solo enseña las dos primeras líneas antes del "más". Ninguna pregunta al final. Añade un comentario para fijar de cinco o seis palabras como máximo.

## 10 · Entrega

Organiza cada entrevista como una serie: `series/NN_invitado_programa/` con `N_nombre.mp4` y `N_nombre.jpg` numerados por orden de publicación, `portadas_tiktok/`, `carruseles/` y un `SERIE.md` con fuente, tramos, clips, copy y notas de producción.

**Enseña, no describas.** Manda al usuario los vídeos y las portadas y espera sus notas: "que termine la frase", "empieza en el 0:07", "aquí quiero verla a ella". Esas notas son lo que más mejora el resultado. Aplícalas con precisión de décimas de segundo, comprobando siempre los tiempos en el metadata.
