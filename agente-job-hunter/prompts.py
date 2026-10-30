GAP_ANALYSIS_PROMPT = """\
Dado el perfil de Adrian (estudiando CAMS, conocimientos en KYC/AML/BSA/FinCEN/OFAC,
buscando rol remoto en crypto compliance), analiza esta oferta e indica:
1) qué requisitos ya cumple
2) qué le falta específicamente
3) una recomendación concreta de cómo cerrar esa brecha

Sé conciso. Máximo 200 palabras en total.

Oferta:
{job_description}
"""
