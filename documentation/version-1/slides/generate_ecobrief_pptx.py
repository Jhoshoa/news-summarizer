from __future__ import annotations

import html
import os
import zipfile
from pathlib import Path


OUT = Path(__file__).with_name("ecobrief-green-tech-pitch.pptx")

SLIDE_W = 13_333_333
SLIDE_H = 7_500_000

TITLE_Y = 760_000
TITLE_H = 1_260_000
SUBTITLE_Y = 2_140_000
CONTENT_Y = 3_030_000

COLORS = {
    "forest": "12372A",
    "green": "1B7F5C",
    "mint": "DDF6E8",
    "lime": "B6E388",
    "cream": "F7F4EA",
    "ink": "17211B",
    "muted": "56635C",
    "white": "FFFFFF",
    "amber": "F2C14E",
    "blue": "006D77",
}


slides = [
    {
        "kicker": "GREEN TECH PITCH",
        "title": "EcoBrief Bolivia",
        "subtitle": "IA responsable para reducir desperdicio digital informativo",
        "bullets": [
            "Menos paginas abiertas",
            "Menos noticias duplicadas",
            "Menos llamadas IA innecesarias",
            "Mas informacion util y medible",
        ],
        "footer": "Josoe Ichuta, Ingenieria  |  Raquel Auza, Digital-Academy",
        "type": "cover",
    },
    {
        "kicker": "PROBLEMA",
        "title": "Informarse consume mas recursos de los necesarios",
        "subtitle": "El problema no es falta de informacion. Es exceso de informacion redundante.",
        "bullets": [
            "Una misma historia se repite en varios medios.",
            "El usuario abre multiples paginas para entender un hecho.",
            "Muchas personas buscan contexto en TikTok, Facebook u otros feeds.",
            "En redes, la informacion puede aparecer fragmentada o sin fuente clara.",
            "Cada pagina carga imagenes, scripts, publicidad y trackers.",
            "La IA desperdicia tokens si procesa contenido repetido.",
        ],
        "callout": "Green Tech tambien es usar mejor software, datos, IA y cloud.",
    },
    {
        "kicker": "OPORTUNIDAD",
        "title": "De ruido digital a informacion esencial",
        "subtitle": "EcoBrief crea una capa de eficiencia entre los medios locales y las personas.",
        "columns": [
            ("Antes", ["Muchas paginas", "Noticias repetidas", "Scroll social", "Impacto invisible"]),
            ("Con EcoBrief", ["Un brief priorizado", "Historias unicas", "Fuentes trazables", "Metricas de reduccion"]),
        ],
    },
    {
        "kicker": "SOLUCION",
        "title": "EcoBrief Bolivia",
        "subtitle": "Una plataforma que recolecta, deduplica, prioriza y resume noticias locales con IA eficiente.",
        "bullets": [
            "Recolecta noticias de medios bolivianos.",
            "Extrae titulo, descripcion, cuerpo, fecha, fuente e imagen.",
            "Elimina duplicados y agrupa historias.",
            "Resume solo los articulos seleccionados.",
            "Mantiene enlace a fuentes originales identificadas.",
            "Entrega briefs por web y prepara distribucion personalizada.",
        ],
        "callout": "La IA se usa despues de reducir el volumen, no antes.",
    },
    {
        "kicker": "PIPELINE",
        "title": "Primero reducimos, luego usamos IA",
        "subtitle": "La eficiencia ocurre antes de llamar al modelo.",
        "steps": [
            "Scraping",
            "Limpieza",
            "Validacion",
            "Dedupe",
            "Ranking",
            "IA",
            "Brief",
            "Impacto",
        ],
    },
    {
        "kicker": "PRODUCTO ACTUAL",
        "title": "MVP funcional, no solo una idea",
        "subtitle": "Backend, frontend, base de datos, scraping real, IA y tests.",
        "bullets": [
            "Home con noticias destacadas y priorizadas.",
            "Listado y detalle de articulos recolectados.",
            "Pagina de impacto Green Tech.",
            "Suscripcion con categorias, canal y frecuencia.",
            "Endpoint manual para generar summaries.",
        ],
        "placeholder": "Insertar captura: Home + Impacto + Suscripcion",
    },
    {
        "kicker": "IMPACTO",
        "title": "Impacto medible y transparente",
        "subtitle": "El sistema mide reduccion operativa y estima ahorro digital de forma conservadora.",
        "columns": [
            ("Metricas reales", ["Recolectadas", "Utiles", "Duplicadas", "Candidatas a IA", "Briefs", "Cache"]),
            ("Metricas estimadas", ["Paginas evitadas", "Minutos ahorrados", "MB no descargados", "Llamadas IA evitadas", "Scroll evitado"]),
        ],
        "callout": "No prometemos medicion energetica directa todavia; mostramos reduccion verificable del flujo.",
    },
    {
        "kicker": "DIFERENCIADORES",
        "title": "Por que EcoBrief es competitivo",
        "subtitle": "Combina Green Tech, producto funcional y bajo costo operativo.",
        "bullets": [
            "Reduce desperdicio digital, no solo resume noticias.",
            "Deduplica, rankea y cachea antes de usar IA.",
            "Muestra impacto con metricas visibles.",
            "Ofrece una alternativa trazable al consumo informativo en redes.",
            "Puede escalar a boletines oficiales y monitoreo institucional.",
            "Equipo interdepartamental con vision tecnica y educativa.",
        ],
    },
    {
        "kicker": "COSTOS",
        "title": "Modelo inicial de bajo costo",
        "subtitle": "Un MVP sostenible puede operar con infraestructura simple y costos variables controlados.",
        "table": [
            ("Servidor Hostinger KVM 2", "USD 107.88/ano ref."),
            ("Dominio NIC Bolivia", "55 Bs/ano"),
            ("BD + backend + frontend + cron", "Incluido en VPS"),
            ("Email Gmail SMTP + App Password", "Gratis con limites"),
            ("Telegram Bot API", "Gratis"),
            ("WhatsApp Twilio", "Piloto/opcional"),
            ("IA Groq API free tier", "USD 0 en demo"),
        ],
    },
    {
        "kicker": "ROADMAP",
        "title": "Expansion con deuda tecnica clara",
        "subtitle": "Lo grande queda como evolucion medible, no como promesa vaga.",
        "columns": [
            ("Corto plazo", ["Metricas historicas", "Fuentes relacionadas", "Alertas de scraping", "Scroll evitado"]),
            ("Mediano plazo", ["Bytes reales evitados", "Telegram/WhatsApp productivo", "Boletines del Estado"]),
            ("Largo plazo", ["Suscripciones pagas", "Panel institucional", "Alertas publicas"]),
        ],
    },
    {
        "kicker": "CIERRE",
        "title": "IA para reducir, no para multiplicar ruido",
        "subtitle": "EcoBrief convierte informacion dispersa en briefs esenciales, medibles y de bajo costo.",
        "bullets": [
            "Resuelve un problema cotidiano.",
            "Encaja directamente con Green Tech.",
            "Tiene MVP funcional.",
            "Puede escalar con costos controlados.",
            "Convierte impacto digital en metricas visibles.",
        ],
        "callout": "Informacion esencial. IA responsable. Eficiencia digital desde Bolivia.",
    },
]


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def emu(v: int) -> str:
    return str(v)


def text_box(
    x: int,
    y: int,
    w: int,
    h: int,
    text: str,
    size: int = 2800,
    color: str = COLORS["ink"],
    bold: bool = False,
    font: str = "Aptos",
    align: str = "l",
) -> str:
    body = []
    for idx, line in enumerate(text.split("\n")):
        if idx:
            body.append("<a:p/>")
        body.append(
            f"""
            <a:p>
              <a:pPr algn="{align}"/>
              <a:r>
                <a:rPr lang="es-BO" sz="{size}" dirty="0">
                  {'<a:b/>' if bold else ''}
                  <a:solidFill><a:srgbClr val="{color}"/></a:solidFill>
                  <a:latin typeface="{font}"/>
                </a:rPr>
                <a:t>{esc(line)}</a:t>
              </a:r>
            </a:p>
            """
        )
    return f"""
    <p:sp>
      <p:nvSpPr><p:cNvPr id="{text_box.next_id()}" name="Text"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
      <p:spPr><a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>
      <p:txBody><a:bodyPr wrap="square" anchor="t"/><a:lstStyle/>{''.join(body)}</p:txBody>
    </p:sp>
    """


def _next_id() -> int:
    _next_id.value += 1
    return _next_id.value


_next_id.value = 10
text_box.next_id = _next_id  # type: ignore[attr-defined]


def rect(x: int, y: int, w: int, h: int, fill: str, line: str | None = None, radius: str = "roundRect") -> str:
    ln = f'<a:ln w="10000"><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln>' if line else "<a:ln><a:noFill/></a:ln>"
    return f"""
    <p:sp>
      <p:nvSpPr><p:cNvPr id="{text_box.next_id()}" name="Shape"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
      <p:spPr>
        <a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>
        <a:prstGeom prst="{radius}"><a:avLst/></a:prstGeom>
        <a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>
        {ln}
      </p:spPr>
      <p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody>
    </p:sp>
    """


def bullet_list(x: int, y: int, w: int, bullets: list[str], color: str = COLORS["ink"]) -> str:
    out = []
    yy = y
    for bullet in bullets:
        out.append(rect(x, yy + 52_000, 95_000, 95_000, COLORS["green"], radius="ellipse"))
        out.append(text_box(x + 155_000, yy, w - 155_000, 260_000, bullet, 2150, color))
        yy += 385_000
    return "".join(out)


def add_header(slide: dict) -> str:
    return (
        rect(0, 0, SLIDE_W, 7_500_000, COLORS["cream"], radius="rect")
        + rect(0, 0, 245_000, SLIDE_H, COLORS["green"], radius="rect")
        + text_box(620_000, 410_000, 3_600_000, 260_000, slide["kicker"], 1350, COLORS["green"], True)
        + text_box(620_000, TITLE_Y, 8_250_000, TITLE_H, slide["title"], 3450, COLORS["forest"], True)
        + text_box(630_000, SUBTITLE_Y, 8_350_000, 620_000, slide.get("subtitle", ""), 1850, COLORS["muted"])
    )


def render_slide(slide: dict, idx: int) -> str:
    global _next_id
    _next_id.value = 10
    shapes = []
    if slide.get("type") == "cover":
        shapes.append(rect(0, 0, SLIDE_W, SLIDE_H, COLORS["forest"], radius="rect"))
        shapes.append(rect(8_850_000, 0, 4_483_333, SLIDE_H, COLORS["green"], radius="rect"))
        shapes.append(rect(9_240_000, 650_000, 2_700_000, 2_700_000, COLORS["lime"], radius="ellipse"))
        shapes.append(rect(9_850_000, 1_250_000, 1_500_000, 1_500_000, COLORS["forest"], radius="ellipse"))
        shapes.append(text_box(620_000, 550_000, 4_300_000, 300_000, slide["kicker"], 1400, COLORS["lime"], True))
        shapes.append(text_box(620_000, 1_150_000, 6_700_000, 950_000, slide["title"], 5200, COLORS["white"], True))
        shapes.append(text_box(630_000, 2_160_000, 6_500_000, 700_000, slide["subtitle"], 2500, COLORS["mint"]))
        shapes.append(bullet_list(660_000, 3_300_000, 5_900_000, slide["bullets"], COLORS["white"]))
        shapes.append(text_box(620_000, 6_780_000, 7_000_000, 260_000, slide["footer"], 1550, COLORS["mint"]))
    else:
        shapes.append(add_header(slide))
        if "bullets" in slide:
            shapes.append(bullet_list(770_000, CONTENT_Y, 6_850_000, slide["bullets"]))
        if "columns" in slide:
            col_count = len(slide["columns"])
            col_w = 3_780_000 if col_count == 3 else 4_950_000
            start_x = 820_000
            gap = 340_000
            for i, (heading, items) in enumerate(slide["columns"]):
                x = start_x + i * (col_w + gap)
                shapes.append(rect(x, CONTENT_Y, col_w, 3_220_000, COLORS["white"], COLORS["mint"]))
                shapes.append(text_box(x + 260_000, CONTENT_Y + 230_000, col_w - 520_000, 340_000, heading, 2200, COLORS["green"], True))
                shapes.append(bullet_list(x + 300_000, CONTENT_Y + 720_000, col_w - 580_000, items, COLORS["ink"]))
        if "steps" in slide:
            x = 720_000
            y = CONTENT_Y + 260_000
            for i, step in enumerate(slide["steps"]):
                shapes.append(rect(x, y, 1_350_000, 760_000, COLORS["white"], COLORS["mint"]))
                shapes.append(text_box(x + 80_000, y + 135_000, 1_190_000, 180_000, f"{i + 1}", 1650, COLORS["green"], True, align="c"))
                shapes.append(text_box(x + 100_000, y + 350_000, 1_150_000, 280_000, step, 1650, COLORS["ink"], True, align="c"))
                if i < len(slide["steps"]) - 1:
                    shapes.append(text_box(x + 1_380_000, y + 250_000, 250_000, 250_000, ">", 2400, COLORS["green"], True, align="c"))
                x += 1_570_000
        if "table" in slide:
            y = CONTENT_Y
            for label, value in slide["table"]:
                fill = COLORS["white"] if (y // 440_000) % 2 else COLORS["mint"]
                shapes.append(rect(830_000, y, 7_350_000, 340_000, fill, radius="rect"))
                shapes.append(text_box(1_050_000, y + 70_000, 4_900_000, 170_000, label, 1700, COLORS["ink"]))
                shapes.append(text_box(6_000_000, y + 70_000, 1_900_000, 170_000, value, 1700, COLORS["forest"], True, align="r"))
                y += 445_000
        if "placeholder" in slide:
            shapes.append(rect(8_250_000, CONTENT_Y, 3_950_000, 2_650_000, COLORS["white"], COLORS["green"]))
            shapes.append(text_box(8_600_000, CONTENT_Y + 870_000, 3_250_000, 620_000, slide["placeholder"], 2100, COLORS["muted"], True, align="c"))
        if "callout" in slide:
            shapes.append(rect(8_500_000, 5_140_000, 3_900_000, 1_150_000, COLORS["forest"]))
            shapes.append(text_box(8_790_000, 5_400_000, 3_320_000, 540_000, slide["callout"], 1950, COLORS["white"], True, align="c"))
        shapes.append(text_box(11_940_000, 6_930_000, 720_000, 220_000, f"{idx:02d}", 1300, COLORS["green"], True, align="r"))
    return slide_xml("".join(shapes))


def slide_xml(shapes: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
      {shapes}
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>
"""


def content_types() -> str:
    overrides = "\n".join(
        f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        for i in range(1, len(slides) + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  {overrides}
  <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
  <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
  <Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""


def rels_root() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""


def presentation() -> str:
    sld_ids = "\n".join(
        f'<p:sldId id="{255 + i}" r:id="rId{i}"/>' for i in range(1, len(slides) + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId{len(slides) + 1}"/></p:sldMasterIdLst>
  <p:sldIdLst>{sld_ids}</p:sldIdLst>
  <p:sldSz cx="{SLIDE_W}" cy="{SLIDE_H}" type="wide"/>
  <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>"""


def presentation_rels() -> str:
    rels = [
        f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>'
        for i in range(1, len(slides) + 1)
    ]
    rels.append(
        f'<Relationship Id="rId{len(slides) + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>'
    )
    rels.append(
        f'<Relationship Id="rId{len(slides) + 2}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>'
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{''.join(rels)}</Relationships>"""


def empty_rels(target: str = "../slideLayouts/slideLayout1.xml") -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="{target}"/>
</Relationships>"""


def master() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld>
  <p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
  <p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>
</p:sldMaster>"""


def layout() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1">
  <p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sldLayout>"""


def theme() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="EcoBrief">
  <a:themeElements>
    <a:clrScheme name="EcoBrief">
      <a:dk1><a:srgbClr val="17211B"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>
      <a:dk2><a:srgbClr val="12372A"/></a:dk2><a:lt2><a:srgbClr val="F7F4EA"/></a:lt2>
      <a:accent1><a:srgbClr val="1B7F5C"/></a:accent1><a:accent2><a:srgbClr val="B6E388"/></a:accent2>
      <a:accent3><a:srgbClr val="F2C14E"/></a:accent3><a:accent4><a:srgbClr val="006D77"/></a:accent4>
      <a:accent5><a:srgbClr val="DDF6E8"/></a:accent5><a:accent6><a:srgbClr val="56635C"/></a:accent6>
      <a:hlink><a:srgbClr val="006D77"/></a:hlink><a:folHlink><a:srgbClr val="1B7F5C"/></a:folHlink>
    </a:clrScheme>
    <a:fontScheme name="Aptos"><a:majorFont><a:latin typeface="Aptos Display"/></a:majorFont><a:minorFont><a:latin typeface="Aptos"/></a:minorFont></a:fontScheme>
    <a:fmtScheme name="EcoBrief"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme>
  </a:themeElements>
  <a:objectDefaults/><a:extraClrSchemeLst/>
</a:theme>"""


def core() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>EcoBrief Bolivia - Green Tech Pitch</dc:title>
  <dc:creator>EcoBrief Bolivia</dc:creator>
  <cp:lastModifiedBy>EcoBrief Bolivia</cp:lastModifiedBy>
</cp:coreProperties>"""


def app() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>EcoBrief PPTX Generator</Application>
  <PresentationFormat>Widescreen</PresentationFormat>
  <Slides>{len(slides)}</Slides>
</Properties>"""


def build() -> None:
    if OUT.exists():
        OUT.unlink()
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types())
        z.writestr("_rels/.rels", rels_root())
        z.writestr("ppt/presentation.xml", presentation())
        z.writestr("ppt/_rels/presentation.xml.rels", presentation_rels())
        z.writestr("ppt/slideMasters/slideMaster1.xml", master())
        z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", empty_rels())
        z.writestr("ppt/slideLayouts/slideLayout1.xml", layout())
        z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>""")
        z.writestr("ppt/theme/theme1.xml", theme())
        z.writestr("docProps/core.xml", core())
        z.writestr("docProps/app.xml", app())
        for i, slide in enumerate(slides, start=1):
            z.writestr(f"ppt/slides/slide{i}.xml", render_slide(slide, i))
            z.writestr(f"ppt/slides/_rels/slide{i}.xml.rels", empty_rels("../slideLayouts/slideLayout1.xml"))
    print(OUT)


if __name__ == "__main__":
    os.chdir(Path(__file__).parent)
    build()
