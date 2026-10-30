from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

OUTPUT = "FATF_40_Recomendaciones.pdf"

doc = SimpleDocTemplate(
    OUTPUT,
    pagesize=A4,
    rightMargin=2*cm,
    leftMargin=2*cm,
    topMargin=2.5*cm,
    bottomMargin=2.5*cm,
    title="Las 40 Recomendaciones del FATF - Resumen CAMS",
    author="Agente CAMS"
)

styles = getSampleStyleSheet()

# Custom styles
title_style = ParagraphStyle(
    "CustomTitle",
    parent=styles["Title"],
    fontSize=22,
    textColor=colors.HexColor("#1a3a5c"),
    spaceAfter=8,
    alignment=TA_CENTER,
    fontName="Helvetica-Bold",
)
subtitle_style = ParagraphStyle(
    "Subtitle",
    parent=styles["Normal"],
    fontSize=12,
    textColor=colors.HexColor("#2e6da4"),
    spaceAfter=4,
    alignment=TA_CENTER,
    fontName="Helvetica",
)
pillar_style = ParagraphStyle(
    "Pillar",
    parent=styles["Heading1"],
    fontSize=14,
    textColor=colors.white,
    spaceAfter=6,
    spaceBefore=14,
    fontName="Helvetica-Bold",
    backColor=colors.HexColor("#1a3a5c"),
    leftIndent=-0.3*cm,
    rightIndent=-0.3*cm,
    borderPad=6,
)
rec_title_style = ParagraphStyle(
    "RecTitle",
    parent=styles["Normal"],
    fontSize=10,
    textColor=colors.HexColor("#1a3a5c"),
    spaceBefore=8,
    spaceAfter=2,
    fontName="Helvetica-Bold",
    leftIndent=0.5*cm,
)
rec_body_style = ParagraphStyle(
    "RecBody",
    parent=styles["Normal"],
    fontSize=9,
    textColor=colors.HexColor("#333333"),
    spaceAfter=4,
    fontName="Helvetica",
    leftIndent=0.5*cm,
    rightIndent=0.2*cm,
    leading=13,
    alignment=TA_JUSTIFY,
)
note_style = ParagraphStyle(
    "Note",
    parent=styles["Normal"],
    fontSize=8,
    textColor=colors.HexColor("#7a3d00"),
    spaceAfter=4,
    fontName="Helvetica-Oblique",
    leftIndent=0.8*cm,
    backColor=colors.HexColor("#fff8e1"),
    borderPad=4,
    borderColor=colors.HexColor("#f0c060"),
    borderWidth=0.5,
    borderRadius=2,
)
footer_style = ParagraphStyle(
    "Footer",
    parent=styles["Normal"],
    fontSize=8,
    textColor=colors.HexColor("#888888"),
    alignment=TA_CENTER,
    fontName="Helvetica-Oblique",
)

def pillar_header(text):
    return [
        Spacer(1, 0.3*cm),
        Paragraph(f"  {text}", pillar_style),
        Spacer(1, 0.1*cm),
    ]

def rec(num, title, body, cams_note=None):
    items = [
        Paragraph(f"R{num}. {title}", rec_title_style),
        Paragraph(body, rec_body_style),
    ]
    if cams_note:
        items.append(Paragraph(f"⭐ CAMS: {cams_note}", note_style))
    items.append(HRFlowable(width="100%", thickness=0.4, color=colors.HexColor("#dddddd"), spaceAfter=2))
    return items

story = []

# ── PORTADA ──────────────────────────────────────────────────────────────────
story.append(Spacer(1, 1.5*cm))
story.append(Paragraph("LAS 40 RECOMENDACIONES DEL FATF", title_style))
story.append(Paragraph("Grupo de Acción Financiera Internacional (GAFI)", subtitle_style))
story.append(Spacer(1, 0.3*cm))
story.append(HRFlowable(width="80%", thickness=2, color=colors.HexColor("#2e6da4"), hAlign="CENTER"))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph("Resumen completo para la certificación CAMS", subtitle_style))
story.append(Paragraph("Preparado en español — Marzo 2026", ParagraphStyle("sm", parent=styles["Normal"], fontSize=9, alignment=TA_CENTER, textColor=colors.grey)))
story.append(Spacer(1, 1*cm))

# Intro box
intro_data = [[
    Paragraph(
        "El FATF (Financial Action Task Force) o GAFI es el organismo intergubernamental que establece los estándares "
        "internacionales para combatir el lavado de dinero (AML), el financiamiento del terrorismo (CFT) y la "
        "proliferación de armas de destrucción masiva. Sus 40 Recomendaciones son el marco de referencia global que "
        "todos los países miembros deben implementar. Son fundamentales para el examen CAMS.",
        ParagraphStyle("intro", parent=styles["Normal"], fontSize=9.5, leading=14,
                       textColor=colors.HexColor("#1a3a5c"), alignment=TA_JUSTIFY)
    )
]]
intro_table = Table(intro_data, colWidths=[16.5*cm])
intro_table.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#e8f0fa")),
    ("BOX", (0,0), (-1,-1), 1, colors.HexColor("#2e6da4")),
    ("LEFTPADDING", (0,0), (-1,-1), 10),
    ("RIGHTPADDING", (0,0), (-1,-1), 10),
    ("TOPPADDING", (0,0), (-1,-1), 10),
    ("BOTTOMPADDING", (0,0), (-1,-1), 10),
    ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.HexColor("#e8f0fa")]),
]))
story.append(intro_table)
story.append(Spacer(1, 0.5*cm))

# Structure overview
story.append(Paragraph("Estructura de las 40 Recomendaciones", ParagraphStyle("secH", parent=styles["Heading2"], fontSize=11, textColor=colors.HexColor("#1a3a5c"))))

_th = ParagraphStyle("th", parent=styles["Normal"], fontSize=9, fontName="Helvetica-Bold",
                     textColor=colors.white, leading=13)
_td_pilar = ParagraphStyle("tdPilar", parent=styles["Normal"], fontSize=9, fontName="Helvetica-Bold",
                            textColor=colors.HexColor("#1a3a5c"), leading=13)
_td_recs  = ParagraphStyle("tdRecs",  parent=styles["Normal"], fontSize=10, fontName="Helvetica-Bold",
                            textColor=colors.HexColor("#2e6da4"), leading=14, alignment=TA_CENTER)
_td_tema  = ParagraphStyle("tdTema",  parent=styles["Normal"], fontSize=9, fontName="Helvetica",
                            textColor=colors.HexColor("#333333"), leading=13)

def _p(text, style): return Paragraph(text, style)

struct_data = [
    [_p("Pilar", _th), _p("Recomendaciones", _th), _p("Tema principal", _th)],
    [_p("A - Políticas AML/CFT\ny coordinación", _td_pilar),       _p("R1-R2",   _td_recs), _p("Evaluación de riesgos\ny cooperación nacional", _td_tema)],
    [_p("B - Lavado de dinero\ny decomiso",       _td_pilar),       _p("R3-R4",   _td_recs), _p("Tipificación penal\ny decomiso de activos", _td_tema)],
    [_p("C - Financiamiento del terrorismo\ny proliferación", _td_pilar), _p("R5-R8",  _td_recs), _p("Delitos de FT/proliferación,\nsanciones y NPOs", _td_tema)],
    [_p("D - Medidas preventivas",                _td_pilar),       _p("R9-R23",  _td_recs), _p("CDD, PEPs, Travel Rule,\nVASPs, DNFBPs", _td_tema)],
    [_p("E - Transparencia y\nbeneficiario final",_td_pilar),       _p("R24-R25", _td_recs), _p("Personas jurídicas\ny fideicomisos (UBO)", _td_tema)],
    [_p("F - Poderes y responsabilidades\nde autoridades", _td_pilar), _p("R26-R35", _td_recs), _p("Supervisión, FIU,\ninvestigación y sanciones", _td_tema)],
    [_p("G - Cooperación internacional",          _td_pilar),       _p("R36-R40", _td_recs), _p("Extradición y\nasistencia legal mutua", _td_tema)],
]
struct_table = Table(struct_data, colWidths=[6*cm, 3*cm, 7.5*cm])
struct_table.setStyle(TableStyle([
    ("BACKGROUND",    (0,0),  (-1,0),  colors.HexColor("#1a3a5c")),
    ("ROWBACKGROUNDS",(0,1),  (-1,-1), [colors.white, colors.HexColor("#f0f5fb")]),
    ("GRID",          (0,0),  (-1,-1), 0.5, colors.HexColor("#cccccc")),
    ("LEFTPADDING",   (0,0),  (-1,-1), 10),
    ("RIGHTPADDING",  (0,0),  (-1,-1), 10),
    ("TOPPADDING",    (0,0),  (-1,-1), 10),
    ("BOTTOMPADDING", (0,0),  (-1,-1), 10),
    ("VALIGN",        (0,0),  (-1,-1), "MIDDLE"),
    ("ALIGN",         (1,0),  (1,-1),  "CENTER"),
]))
story.append(struct_table)
story.append(PageBreak())

# ─────────────────────────────────────────────────────────────────────────────
# PILAR A: R1–R2
# ─────────────────────────────────────────────────────────────────────────────
story += pillar_header("PILAR A — Políticas AML/CFT y Coordinación Nacional (R1–R2)")

story += rec(1, "Evaluación de riesgos y aplicación de enfoque basado en riesgo (RBA)",
    "Los países deben identificar, evaluar y comprender los riesgos de lavado de dinero y financiamiento del "
    "terrorismo que enfrentan. Con base en esa evaluación, deben aplicar medidas proporcionales a los riesgos "
    "identificados: mayor atención donde el riesgo es alto, medidas simplificadas donde es bajo. Las instituciones "
    "financieras también deben realizar sus propias evaluaciones de riesgo.",
    "El RBA (Risk-Based Approach) es un concepto central del CAMS. Debes saber que R1 es el fundamento de todo el marco.")

story += rec(2, "Cooperación y coordinación nacional",
    "Cada país debe contar con políticas AML/CFT coordinadas entre todas las autoridades competentes: unidad de "
    "inteligencia financiera (FIU), fuerzas del orden, supervisores y otras autoridades. Debe existir un mecanismo "
    "formal de coordinación y cooperación.")

# ─────────────────────────────────────────────────────────────────────────────
# PILAR B: R3–R4
# ─────────────────────────────────────────────────────────────────────────────
story += pillar_header("PILAR B — Lavado de Dinero y Decomiso (R3–R4)")

story += rec(3, "Tipificación del delito de lavado de dinero",
    "El lavado de dinero debe ser tipificado como delito penal conforme a la Convención de Viena (1988) y la "
    "Convención de Palermo (2000). El delito debe aplicarse a todos los delitos graves como delitos precedentes "
    "(predicados), incluyendo los cometidos en otro país. También deben sancionarse personas jurídicas (no solo "
    "individuos).",
    "Recuerda las tres fases del LD: placement (colocación), layering (estratificación), integration (integración).")

story += rec(4, "Decomiso y medidas provisionales",
    "Los países deben contar con leyes que permitan a las autoridades identificar, rastrear, congelar, incautar y "
    "decomisar los activos producto del crimen, incluyendo bienes de valor equivalente. Deben poder aplicar medidas "
    "cautelares sin notificar previamente al sospechoso para evitar fuga de activos.")

# ─────────────────────────────────────────────────────────────────────────────
# PILAR C: R5–R8
# ─────────────────────────────────────────────────────────────────────────────
story += pillar_header("PILAR C — Financiamiento del Terrorismo y Proliferación (R5–R8)")

story += rec(5, "Tipificación del financiamiento del terrorismo (FT)",
    "El FT debe ser un delito penal autónomo, independientemente de si el acto terrorista llegó a ocurrir o si los "
    "fondos son de origen lícito o ilícito. Deben sancionarse también intentos, complicidad y organizaciones "
    "terroristas.",
    "Diferencia clave: en FT los fondos pueden ser lícitos (ej. donativos). En LD el dinero es siempre de origen ilícito.")

story += rec(6, "Sanciones financieras dirigidas relacionadas con terrorismo y FT",
    "Los países deben implementar sin demora las sanciones del Consejo de Seguridad de la ONU (Resoluciones 1267, "
    "1373 y sucesoras). Esto implica congelar activos y prohibir transacciones con personas/entidades designadas "
    "en listas como la SDN de OFAC. El congelamiento debe ser inmediato ('sin demora').")

story += rec(7, "Sanciones financieras dirigidas relacionadas con proliferación de armas",
    "Similar a R6 pero aplica a la financiación de la proliferación de armas de destrucción masiva (ADM). Los "
    "países deben implementar las sanciones de la ONU (Resoluciones 1718 y 1737) para congelar activos de personas "
    "y entidades vinculadas a programas de armas nucleares, biológicas o químicas.")

story += rec(8, "Organizaciones sin fines de lucro (NPOs)",
    "Las NPOs (ONGs, fundaciones, asociaciones) son vulnerables al abuso para el financiamiento del terrorismo. "
    "Los países deben revisar su sector de NPOs y aplicar medidas focalizadas en las que presenten mayor riesgo, "
    "sin imponer cargas desproporcionadas al sector en general.",
    "Enfoque basado en riesgo: no regular todas las NPOs igual, sino identificar cuáles son vulnerables.")

# ─────────────────────────────────────────────────────────────────────────────
# PILAR D: R9–R23
# ─────────────────────────────────────────────────────────────────────────────
story += pillar_header("PILAR D — Medidas Preventivas para Instituciones Financieras (R9–R23)")

story += rec(9, "Leyes sobre secreto bancario",
    "Las leyes de secreto bancario no deben inhibir la implementación de las Recomendaciones del FATF. Las "
    "obligaciones de confidencialidad no pueden ser usadas como escudo para bloquear el intercambio de información "
    "entre instituciones financieras y autoridades competentes.")

story += rec(10, "Debida diligencia del cliente (CDD)",
    "Las instituciones financieras deben aplicar CDD al: establecer relaciones de negocio, realizar transacciones "
    "ocasionales ≥ USD/EUR 15,000 (o transferencias ≥ 1,000), cuando haya sospecha de LD/FT, o cuando haya dudas "
    "sobre la veracidad de la información. CDD incluye: identificar y verificar al cliente, identificar al "
    "beneficiario final (UBO), entender el propósito de la relación y monitoreo continuo.",
    "R10 es una de las más importantes del CAMS. UBO = Ultimate Beneficial Owner. Umbral de USD 15,000 para transacciones ocasionales.")

story += rec(11, "Mantenimiento de registros",
    "Las instituciones financieras deben mantener registros de transacciones y documentos de CDD por al menos "
    "5 años desde el fin de la relación o de la transacción ocasional. Los registros deben ser suficientes para "
    "reconstruir transacciones individuales y servir como evidencia en caso de procesamiento penal.")

story += rec(12, "Personas Expuestas Políticamente (PEPs)",
    "Las instituciones financieras deben aplicar medidas de EDD (Enhanced Due Diligence) a las PEPs extranjeras "
    "y sus familiares/asociados cercanos: obtener aprobación de alta dirección, establecer el origen de los "
    "fondos y monitoreo reforzado. Para PEPs nacionales y de organizaciones internacionales, se aplica un enfoque "
    "basado en riesgo.",
    "PEP extranjero = siempre EDD. PEP nacional = según riesgo. El riesgo de corrupción es la razón principal.")

story += rec(13, "Banca corresponsal",
    "Para relaciones de banca corresponsal transfronterizas, las instituciones deben: recopilar información "
    "suficiente sobre el banco respondiente, evaluar su reputación y controles AML/CFT, obtener aprobación de "
    "alta gerencia, y no mantener relaciones con bancos pantalla (shell banks). Prohibido el anidamiento "
    "(payable-through accounts que permitan a terceros usar la cuenta).",
    "Shell bank: banco sin presencia física real. Prohibido bajo R13. Muy relevante para el CAMS.")

story += rec(14, "Servicios de transferencia de dinero o valor (MVTS)",
    "Los países deben exigir que los proveedores de MVTS (money or value transfer services) estén registrados "
    "o con licencia y sujetos a supervisión AML/CFT. Deben mantener una lista de agentes. Las jurisdicciones "
    "deben cooperar para supervisar redes de transferencia informales (hawala, etc.).")

story += rec(15, "Nuevas tecnologías (incluye VASPs y activos virtuales)",
    "Los países e instituciones financieras deben identificar y evaluar los riesgos de LD/FT asociados a nuevas "
    "tecnologías, incluyendo activos virtuales (criptomonedas). Los VASPs (Virtual Asset Service Providers) deben "
    "estar registrados/autorizados y sujetos a las mismas obligaciones AML/CFT que las instituciones financieras, "
    "incluyendo la Travel Rule.",
    "⚠️ Muy relevante para cripto: R15 fue actualizada en 2019 para incluir VASPs explícitamente. Los VASPs deben aplicar CDD, reportar SARs, cumplir Travel Rule.")

story += rec(16, "Transferencias electrónicas (Travel Rule / Wire Transfer Rule)",
    "Las instituciones financieras que realizan transferencias electrónicas deben incluir y transmitir información "
    "del ordenante Y del beneficiario: nombre, número de cuenta, dirección, documento de identidad, número de "
    "identificación de cliente o fecha/lugar de nacimiento. Umbral: sin límite para transferencias internacionales "
    "(toda transferencia debe llevar la información); USD 3,000 para domésticas. Aplica también a VASPs en "
    "transferencias de activos virtuales.",
    "Travel Rule para cripto: el VASP originante debe enviar datos del remitente y beneficiario al VASP receptor. Umbral: USD/EUR 1,000 según jurisdicción.")

story += rec(17, "Dependencia en terceros",
    "Las instituciones financieras pueden depender de terceros (agentes, intermediarios) para realizar la CDD, "
    "siempre que el tercero esté regulado y supervisado para AML/CFT. La responsabilidad final recae siempre en "
    "la institución financiera que depende del tercero, no en el tercero mismo.")

story += rec(18, "Controles internos y grupos financieros",
    "Las instituciones financieras deben implementar programas AML/CFT internos que incluyan: políticas y "
    "procedimientos, programa de auditoría interna, función de cumplimiento con un oficial responsable, "
    "capacitación continua a empleados, y screening de empleados. Los grupos financieros deben aplicar políticas "
    "grupales en todas sus subsidiarias, incluyendo las del extranjero.")

story += rec(19, "Países de alto riesgo",
    "Las instituciones financieras deben aplicar EDD en relaciones con personas, negocios o instituciones "
    "financieras de países identificados por el FATF como de alto riesgo (lista negra o gris). Los países "
    "pueden prohibir o restringir relaciones con jurisdicciones de alto riesgo.",
    "Lista negra FATF (High-Risk Jurisdictions): acción requerida. Lista gris (Increased Monitoring): vigilancia reforzada.")

story += rec(20, "Reporte de operaciones sospechosas (SAR/STR)",
    "Las instituciones financieras deben reportar a la FIU cuando sospechen que fondos son producto de actividad "
    "criminal o están relacionados con FT, independientemente del monto. El reporte debe ser confidencial "
    "(tipping off prohibido). Aplica a intentos de transacción también.",
    "SAR = Suspicious Activity Report (EE.UU.) / STR = Suspicious Transaction Report (terminología FATF).")

story += rec(21, "Tipping off y confidencialidad",
    "Las instituciones financieras y sus empleados que reporten SARs de buena fe deben estar protegidos de "
    "responsabilidad legal. Está prohibido revelar al cliente o a terceros que se presentó un SAR o que se está "
    "realizando una investigación ('tipping off'). El tipping off es un delito en la mayoría de jurisdicciones.")

story += rec(22, "DNFBPs — Debida diligencia",
    "Las mismas obligaciones de CDD y mantenimiento de registros de R10–R12 aplican a los negocios y profesiones "
    "no financieros designados (DNFBPs): casinos, agentes inmobiliarios, comerciantes de metales/piedras preciosas "
    "(transacciones ≥ USD 15,000 en efectivo), notarios, abogados, contadores y proveedores de servicios a "
    "empresas (TCSPs).",
    "DNFBPs son un tema frecuente en el examen CAMS. Recuerda los sectores: CARTAN (Casinos, Agentes inmobiliarios, Raros metales, Trust services, Abogados/contadores, Notarios).")

story += rec(23, "DNFBPs — Otras medidas",
    "Los DNFBPs también deben cumplir con las obligaciones de reporte de operaciones sospechosas (R20), controles "
    "internos (R18) y cumplimiento en jurisdicciones de alto riesgo (R19). Sin embargo, los abogados y contadores "
    "pueden estar exentos del reporte cuando la información es cubierta por el privilegio profesional legal.")

story.append(PageBreak())

# ─────────────────────────────────────────────────────────────────────────────
# PILAR E: R24–R25
# ─────────────────────────────────────────────────────────────────────────────
story += pillar_header("PILAR E — Transparencia y Beneficiario Final (R24–R25)")

story += rec(24, "Transparencia de personas jurídicas (beneficiario final)",
    "Los países deben asegurar que existe información adecuada, precisa y actualizada sobre el beneficiario final "
    "(UBO) de las personas jurídicas (sociedades, corporaciones). Esta información debe estar disponible para las "
    "autoridades competentes de manera oportuna. Los registros pueden ser públicos o mantenidos por las propias "
    "empresas o intermediarios con acceso regulado.",
    "UBO: persona natural que posee o controla ≥ 25% de una empresa (umbral común, varía por jurisdicción). Tema central en compliance corporativo.")

story += rec(25, "Transparencia de fideicomisos y otras estructuras jurídicas",
    "Similar a R24 pero para fideicomisos (trusts) y otras estructuras como fundaciones. Los países donde se "
    "constituyen o administran estos instrumentos deben asegurar que existe información sobre el settlor, "
    "trustees, protector y beneficiarios. Los trustees deben divulgar su estatus a instituciones financieras "
    "cuando establezcan relaciones de negocio.",
    "Los trusts han sido históricamente usados para ocultar titularidad real. R25 busca cerrar ese vacío.")

# ─────────────────────────────────────────────────────────────────────────────
# PILAR F: R26–R35
# ─────────────────────────────────────────────────────────────────────────────
story += pillar_header("PILAR F — Poderes y Responsabilidades de Autoridades Competentes (R26–R35)")

story += rec(26, "Regulación y supervisión de instituciones financieras",
    "Los países deben asegurar que las instituciones financieras están sujetas a regulación y supervisión AML/CFT "
    "adecuada. Los supervisores deben tener poderes suficientes para monitorear el cumplimiento y aplicar "
    "sanciones. Deben aplicar un enfoque basado en riesgo para priorizar recursos supervisores.")

story += rec(27, "Poderes de los supervisores",
    "Los supervisores financieros deben tener poderes para: realizar inspecciones, exigir información, aplicar "
    "sanciones (administrativas, civiles y penales), retirar licencias y designar administradores. Las sanciones "
    "deben ser efectivas, proporcionales y disuasorias.")

story += rec(28, "Regulación y supervisión de DNFBPs",
    "Los DNFBPs también deben estar sujetos a supervisión AML/CFT efectiva. Los supervisores deben asegurarse "
    "de que los DNFBPs cumplen con sus obligaciones. Para los casinos, se requiere supervisión específica dada "
    "su alta vulnerabilidad al lavado de dinero.")

story += rec(29, "Unidades de Inteligencia Financiera (FIU)",
    "Cada país debe contar con una FIU que reciba, analice y transmita reportes de operaciones sospechosas "
    "(SARs/STRs) e información relacionada con LD/FT. La FIU debe ser el centro nacional de recepción y análisis "
    "de información financiera. Debe ser operativamente independiente y tener acceso a información relevante.",
    "El Grupo Egmont es la red de FIUs a nivel mundial (más de 170 miembros). En EE.UU. la FIU es FinCEN.")

story += rec(30, "Responsabilidades de las autoridades del orden público e investigación",
    "Los países deben garantizar que las agencias de orden público tienen capacidad para investigar LD, FT y "
    "delitos conexos. Deben poder usar técnicas especiales de investigación como operaciones encubiertas, "
    "interceptación de comunicaciones, acceso a datos computacionales y entregas vigiladas.")

story += rec(31, "Poderes de las autoridades de investigación y de orden público",
    "Las autoridades competentes deben tener acceso a toda la información relevante necesaria para sus "
    "investigaciones, incluyendo registros financieros, información de CDD de instituciones financieras, e "
    "información de FIUs de otros países. No deben existir restricciones excesivas al acceso a esta información.")

story += rec(32, "Portadores de efectivo",
    "Los países deben implementar sistemas para detectar el transporte físico transfronterizo de efectivo e "
    "instrumentos negociables al portador. Se recomienda un sistema de declaración obligatoria o divulgación "
    "para montos ≥ USD/EUR 15,000. Las autoridades deben poder detener o decomisar efectivo no declarado o "
    "de origen sospechoso.",
    "Currency declaration at borders: umbral de 10,000 USD en EE.UU. (bajo BSA/FinCEN). El umbral FATF es 15,000.")

story += rec(33, "Estadísticas",
    "Los países deben mantener estadísticas comprensivas sobre: SARs recibidas y analizadas, investigaciones "
    "de LD/FT, procesamiento penal y condenas, activos congelados/incautados/decomisados y asistencia legal "
    "mutua brindada/recibida. Estas estadísticas sirven para evaluar la efectividad del sistema AML/CFT.")

story += rec(34, "Guías y retroalimentación",
    "Las autoridades competentes y supervisores deben proporcionar guías y orientación a las instituciones "
    "financieras y DNFBPs sobre sus obligaciones AML/CFT, incluyendo información sobre tipologías y métodos "
    "de LD/FT actuales. También deben dar retroalimentación sobre la calidad y utilidad de los SARs reportados.")

story += rec(35, "Sanciones",
    "Los países deben contar con un régimen de sanciones efectivo, proporcional y disuasorio para personas "
    "físicas y jurídicas que no cumplan con las obligaciones AML/CFT. Las sanciones pueden ser penales, civiles "
    "o administrativas y deben aplicarse tanto a la institución como a sus directivos.")

# ─────────────────────────────────────────────────────────────────────────────
# PILAR G: R36–R40
# ─────────────────────────────────────────────────────────────────────────────
story += pillar_header("PILAR G — Cooperación Internacional (R36–R40)")

story += rec(36, "Instrumentos internacionales",
    "Los países deben ratificar e implementar plenamente los principales convenios internacionales: Convención "
    "de Viena (1988), Convención de Palermo (2000), Convención de Mérida contra la corrupción (2003), y el "
    "Convenio Internacional para la Supresión del Financiamiento del Terrorismo (1999).",
    "Convención de Viena: primera en tipificar LD relacionado con narcotráfico. Base histórica de todo el marco AML.")

story += rec(37, "Asistencia legal mutua (MLA)",
    "Los países deben prestar la asistencia legal mutua más amplia posible en investigaciones de LD/FT, "
    "incluyendo la recolección de evidencia, entrevistas de testigos, búsqueda de locales, incautación y "
    "decomiso de activos. No deben rechazar solicitudes de MLA basándose en secreto bancario.")

story += rec(38, "Asistencia legal mutua: congelamiento y decomiso",
    "Los países deben contar con autoridad para ejecutar solicitudes de otro país para identificar, congelar, "
    "incautar y decomisar activos producto del crimen. Deben poder compartir los activos decomisados con "
    "países que hayan contribuido a su identificación.")

story += rec(39, "Extradición",
    "Los países deben contar con procedimientos de extradición eficientes y ejecutarlos para delitos de LD/FT. "
    "El LD y FT deben ser delitos extraditables. Los países no deben usar argumentos de 'delito político' para "
    "rechazar extradiciones relacionadas con terrorismo. Si un país no puede extraditar, debe poder enjuiciar "
    "al sospechoso (principio 'extraditar o enjuiciar').")

story += rec(40, "Otras formas de cooperación internacional",
    "Las autoridades competentes (FIUs, supervisores, fuerzas del orden) deben cooperar rápidamente con sus "
    "homólogos en el extranjero para intercambiar información relevante para investigaciones AML/CFT, "
    "independientemente de si existe un tratado formal. Las FIUs deben poder intercambiar información a través "
    "de la Red Egmont. Los supervisores deben poder compartir información con supervisores extranjeros.",
    "Cooperación FIU-a-FIU: la Red Egmont facilita este intercambio entre las más de 170 FIUs miembros.")

# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA FINAL: RESUMEN RÁPIDO
# ─────────────────────────────────────────────────────────────────────────────
story.append(PageBreak())
story.append(Paragraph("Tabla de Referencia Rápida — Las 40 Recomendaciones", title_style))
story.append(Spacer(1, 0.4*cm))

quick_data = [
    ["#", "Título clave", "Concepto esencial"],
    ["R1", "Evaluación de riesgos (RBA)", "Proporcionar esfuerzo según nivel de riesgo"],
    ["R2", "Coordinación nacional", "Políticas AML/CFT coordinadas entre autoridades"],
    ["R3", "Delito de lavado de dinero", "Tipificación penal; todos los delitos graves como predicados"],
    ["R4", "Decomiso", "Congelar, incautar y decomisar productos del crimen"],
    ["R5", "Delito de FT", "FT como delito autónomo; fondos pueden ser lícitos"],
    ["R6", "Sanciones por terrorismo", "Implementar listas ONU sin demora; congelar activos"],
    ["R7", "Sanciones por proliferación ADM", "Congelar activos vinculados a armas de destrucción masiva"],
    ["R8", "NPOs", "Supervisar NPOs vulnerables al financiamiento terrorista"],
    ["R9", "Secreto bancario", "No puede bloquear implementación del FATF"],
    ["R10", "CDD", "Identificar cliente, UBO, propósito; monitoreo continuo; umbral 15k"],
    ["R11", "Registros", "Conservar 5 años mínimo"],
    ["R12", "PEPs", "EDD para PEPs extranjeros; RBA para PEPs nacionales"],
    ["R13", "Banca corresponsal", "EDD; prohibir shell banks y payable-through accounts"],
    ["R14", "MVTS", "Registrar/licenciar proveedores de transferencia de valor"],
    ["R15", "Nuevas tecnologías / VASPs", "VASPs regulados igual que instituciones financieras; RBA"],
    ["R16", "Travel Rule (wire transfers)", "Incluir datos ordenante y beneficiario en transferencias; VASPs"],
    ["R17", "Terceros", "Se puede delegar CDD; responsabilidad siempre recae en institución"],
    ["R18", "Controles internos", "Programa AML, oficial de cumplimiento, capacitación, screening"],
    ["R19", "Países de alto riesgo", "EDD obligatorio; respetar listas negra y gris FATF"],
    ["R20", "SARs", "Reportar sospechas a FIU sin importar monto"],
    ["R21", "Tipping off", "Prohibido revelar que se presentó SAR; protección al reportante"],
    ["R22", "DNFBPs — CDD", "Mismas obligaciones CDD que instituciones financieras"],
    ["R23", "DNFBPs — Otras medidas", "SARs, controles internos; excepción por privilegio legal"],
    ["R24", "Beneficiario final (personas jurídicas)", "UBO: ≥25% control/propiedad; información accesible"],
    ["R25", "Beneficiario final (fideicomisos)", "Trustees deben divulgar; registro de settlor, beneficiarios"],
    ["R26", "Supervisión financiera", "Supervisores con poderes AML/CFT; enfoque basado en riesgo"],
    ["R27", "Poderes supervisores", "Inspección, sanciones, retiro de licencias"],
    ["R28", "Supervisión DNFBPs", "Supervisión AML/CFT efectiva incluyendo casinos"],
    ["R29", "FIU", "Recibir, analizar y diseminar SARs; independencia operativa"],
    ["R30", "Fuerzas del orden", "Capacidad investigativa; técnicas especiales"],
    ["R31", "Poderes investigativos", "Acceso a registros financieros e información CDD"],
    ["R32", "Portadores de efectivo", "Declaración fronteriza ≥15k; decomiso si sospechoso"],
    ["R33", "Estadísticas", "Mantener datos sobre SARs, decomisos, condenas"],
    ["R34", "Guías y retroalimentación", "Orientar a instituciones; retroalimentar sobre calidad SARs"],
    ["R35", "Sanciones", "Sanciones efectivas, proporcionales y disuasorias"],
    ["R36", "Instrumentos internacionales", "Ratificar Viena, Palermo, Mérida y Convenio FT"],
    ["R37", "MLA", "Asistencia legal mutua; secreto bancario no es excusa"],
    ["R38", "MLA — Decomiso", "Ejecutar solicitudes de congelamiento y decomiso extranjeras"],
    ["R39", "Extradición", "Extraditar o enjuiciar; LD y FT son extraditables"],
    ["R40", "Cooperación internacional", "Intercambio de información entre FIUs, supervisores y policías"],
]

col_widths = [1*cm, 4.5*cm, 11*cm]
quick_table = Table(quick_data, colWidths=col_widths, repeatRows=1)
quick_table.setStyle(TableStyle([
    ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1a3a5c")),
    ("TEXTCOLOR", (0,0), (-1,0), colors.white),
    ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
    ("FONTSIZE", (0,0), (-1,-1), 7.5),
    ("FONTNAME", (0,1), (0,-1), "Helvetica-Bold"),
    ("TEXTCOLOR", (0,1), (0,-1), colors.HexColor("#1a3a5c")),
    ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f0f5fb")]),
    ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#cccccc")),
    ("LEFTPADDING", (0,0), (-1,-1), 5),
    ("RIGHTPADDING", (0,0), (-1,-1), 5),
    ("TOPPADDING", (0,0), (-1,-1), 3),
    ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ("VALIGN", (0,0), (-1,-1), "TOP"),
]))
story.append(quick_table)

story.append(Spacer(1, 0.8*cm))
story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#2e6da4")))
story.append(Spacer(1, 0.3*cm))
story.append(Paragraph(
    "Documento preparado para estudio CAMS — Agente CAMS | Marzo 2026 | "
    "Basado en las 40 Recomendaciones del FATF (revisión 2012, actualización 2019 con VASPs)",
    footer_style
))

doc.build(story)
print(f"PDF generado: {OUTPUT}")
