# CAMS Study Plan — Adrian Ontiveros
_Generated: 2026-05-14 | Based on: Candidate Handbook (VCB26.16) + mi_perfil.json_
_Nota de datos: mi_perfil.json tiene estado_confirmacion: estimado. Skills usados como base de diagnóstico, no como confirmacion de nivel de examen._

---

## Estado de logs de estudio

Sin actividad registrada en `study_logs/`. Este plan parte del perfil declarado, no de scores reales. En cuanto completes la primera sesión, registrala para calibrar ritmo real.

---

## 1. Diagnóstico: dominio actual vs. brechas reales

### Estructura del examen (120 preguntas, 3.5 horas, passing score: 75)

| Dominio | Peso | Preguntas aprox. |
|---|---|---|
| A — Understanding Risks and Methods of Financial Crime | 30% | 36 |
| B — Global AFC Frameworks, Governance, and Regulations | 20% | 24 |
| C — Building an Anti-Financial Crime Compliance Program | 30% | 36 |
| D — Tools and Technologies to Fight Financial Crime | 20% | 24 |

Para pasar necesitas responder correctamente ~90 de 120 preguntas.

---

### Skills confirmados de Adrian y su cobertura por dominio

| Skill declarado | Dominio cubierto | Cobertura estimada |
|---|---|---|
| KYC / CDD / EDD | C (items 13, 15) + D (items 4, 5, 7) | Parcial — falta arquitectura de programa |
| AML / BSA | C (item 2) + B (item 8) | Parcial — falta risk appetite statement, RAS |
| OFAC / Sanctions screening | A (item 4) + B (items 2, 9) + D (items 6, 9) | Sólido en conceptos, débil en framework operativo |
| SAR | C (item 18) | Parcial — falta tipping off, escalation timeline |
| FATF / 40 Recomendaciones | B (item 1) | Parcial — falta aplicación a jurisdicciones APAC/EU |
| Travel Rule | A (item 11) + D (item 10) | Parcial — aplica a cripto, falta contexto SWIFT/VASP global |
| Risk assessment | C (items 4, 5, 14) | Débil — RAS formal, enterprise risk, KRIs/KPIs no dominados |
| Blockchain / DeFi | A (item 11) + D (items 10, 11) | Fuerte en práctica, débil en terminología regulatoria formal |

### Diagnóstico por dominio

**Dominio A — Risks and Methods (30% del examen)**
- Strengths: esquemas de ML (placement/layering/integration), VASP, cripto tipologías, sanctions
- Gaps: sectores no-crypto (real estate, gaming, trusts, gatekeepers, accountants, MSBs/PSPs), PEPs formales, predicate crimes como framework legal
- Nivel estimado: 55-65% de cobertura

**Dominio B — Global AFC Frameworks (20% del examen)**
- Strengths: FATF conceptual, OFAC/FinCEN/BSA
- Gaps: UN sanctions regimes en detalle, FIUs y su rol cross-border, PPP (public-private partnerships), regulacion EU/APAC (MiCA, AMLD6, MAS Singapore), ESG/data privacy intersection con AML
- Nivel estimado: 50-60% de cobertura

**Dominio C — Building an AFC Compliance Program (30% del examen)**
- Strengths: KYC/CDD/EDD operativo, SAR writing, transaction monitoring conceptual
- Gaps: Risk Appetite Statement (RAS) formal, three lines of defense model, governing committees, KPIs/KRIs para boards, tipping off rules, FinCEN 314a/314b procedures, COSMIC (Singapore), exit controls, employee due diligence
- Nivel estimado: 45-55% de cobertura — **DOMINIO MAS DEBIL**

**Dominio D — Tools and Technologies (20% del examen)**
- Strengths: blockchain transaction screening, AI/ML awareness, digital onboarding (KYC-tech)
- Gaps: rules-based vs. ML-based TM systems (ATL/BTL tuning, scenario coverage), network analysis tools formales, fuzzy logic en sanctions screening, vendor selection criteria, data quality frameworks
- Nivel estimado: 50-60% de cobertura

### Veredicto de diagnóstico

Adrian tiene base conceptual sólida en KYC/sanctions/cripto pero le faltan los elementos de **programa institucional** (Dominio C) y **regulacion internacional comparada** (Dominio B). El riesgo es confundir conocimiento operativo con conocimiento de examen — CAMS pregunta sobre cómo se construye y gobierna un programa AFC, no solo sobre cómo opera en la línea.

---

## 2. Fases de estudio — ordenadas de más débil a más fuerte

**Ritmo base:** 1 hora/día = ~30 horas/mes
**Total estimado de horas necesarias:** 90-110 horas (candidato con base previa, sin experiencia profesional formal)
**Semanas disponibles hasta meta de examen:** ver Fase 4 abajo

---

### FASE 1 — Dominio C: Building an AFC Compliance Program
**Prioridad: ALTA | Peso: 30% | Semanas: 4**
_El dominio con mayor peso y mayor brecha. Atacarlo primero maximiza el ROI de horas._

**Semana 1 — Program Architecture**
- Three lines of defense: definicion, roles, responsabilidades
- BSA Officer / MLRO: obligaciones legales, diferencia entre jurisdicciones
- Policies vs. standards vs. procedures — como se diferencian y que contienen
- Governing committees: structure, terms of reference, roles en decision-making
- Metodo Chunk & Draw: cuaderno, dos colores, notas en ingles

**Semana 2 — Risk Framework**
- Risk Appetite Statement (RAS): como se define, como se comunica, como se implementa en controles
- Enterprise risk assessment: inherent risk → residual risk, controles intermedios
- Risk-based approach (RBA): como prioriza recursos en un programa AFC
- KPIs y KRIs: que mide cada uno, como se reporta a boards y comites

**Semana 3 — Customer Lifecycle Controls**
- CDD/EDD: arquitectura completa desde onboarding hasta exit controls
- PEPs: identificacion, categorias, controles aplicables
- Tipping off: que esta prohibido, consecuencias, como manejar RFIs con clientes
- Transaction monitoring: rule-based, alertas, investigacion, escalation timelines
- SAR: cuando escribir, estructura, timelines legales por jurisdiccion (US vs EU)

**Semana 4 — Institutional Operations**
- FinCEN 314a / 314b: diferencias, obligaciones, como responder
- EU Regulation 2024/1624 y COSMIC (Singapore): conceptos clave
- Employee due diligence e insider threats
- De-risking: que es, cuando aplica, implicaciones de financial inclusion
- Staff training: obligaciones, frecuencia, contenido minimo

**Checkpoint Fase 1:** quiz de 30 preguntas sobre Dominio C. Meta: 70%+ antes de avanzar.

---

### FASE 2 — Dominio A: Risks and Methods of Financial Crime
**Prioridad: ALTA | Peso: 30% | Semanas: 3**
_Empatar la segunda prioridad con el segundo dominio de mayor peso._

**Semana 5 — Sectores de alto riesgo (no-crypto)**
- Banking high-risk sectors: correspondent banking, shell companies
- PEPs y high-risk customers como categorias de riesgo
- Real estate: tipologias de ML, uso de gatekeepers
- MSBs / PSPs / ecommerce: riesgos especificos y controles esperados
- Trusts y company service providers: opacidad de beneficiario final

**Semana 6 — Sectores especializados**
- Gaming y gambling: tipologias, jurisdicciones relevantes
- Insurance: placement via primas, tipologias de ML
- Accountants como gatekeepers: vulnerabilidades, obligaciones
- Trade-based ML: invoice manipulation, over/under-invoicing
- Predicate crimes: lista FATF, como se vinculan a ML

**Semana 7 — Cripto y VASP (area de ventaja de Adrian)**
- VASP definition formal FATF: que entra, que no
- Travel Rule: $1,000 threshold, VASP-to-VASP obligations, implementacion por jurisdiccion
- Crypto tipologias: mixing, chain-hopping, NFT ML, DeFi risks
- Blockchain analytics: tracing tools, red flags en transacciones
- CFT (Countering Financing of Terrorism): diferencia de motivacion vs ML clasico

**Checkpoint Fase 2:** quiz de 36 preguntas sobre Dominio A. Meta: 72%+ antes de avanzar.

---

### FASE 3 — Dominio B: Global AFC Frameworks
**Prioridad: MEDIA-ALTA | Peso: 20% | Semanas: 2**

**Semana 8 — FATF y organismos internacionales**
- FATF: 40 Recomendaciones en detalle, mutual evaluations, FATF grey/black list
- Regional bodies: MONEYVAL, GAFILAT, APG, ESAAMLG — rol y diferencias
- UN sanctions regimes: Security Council, Consolidated List, diferencia vs OFAC
- FIUs: definicion, rol en investigaciones, Egmont Group
- National y sectoral risk assessments: como impactan el RBA de una institucion

**Semana 9 — Regulacion por jurisdiccion y frameworks emergentes**
- US: BSA, USA PATRIOT Act, FinCEN regulations, OFAC authorities
- EU: AMLD6, Regulation 2024/1624, EBA guidelines, MiCA para VASPs
- APAC: MAS (Singapore), JAFIO (Japan), AUSTRAC (Australia)
- PPP (Public-Private Partnerships): Fin-CEN Exchange, JMLIT (UK) — fortalezas y limitaciones
- ESG, data privacy (GDPR) y su interseccion con AFC obligations

**Checkpoint Fase 3:** quiz de 24 preguntas sobre Dominio B. Meta: 70%+ antes de avanzar.

---

### FASE 4 — Dominio D: Tools and Technologies
**Prioridad: MEDIA | Peso: 20% | Semanas: 2**
_Adrian tiene base técnica real — esta fase es de terminologia formal, no de conceptos nuevos._

**Semana 10 — Transaction Monitoring y Screening Systems**
- Rules-based TM: scenario design, threshold setting, ATL/BTL methodology
- Segmentacion de clientes para TM: por producto, canal, geography
- Transition a ML-based TM: cuando aplicar, model risk management
- Sanctions screening: fuzzy logic, false positive management, list management
- Blockchain transaction monitoring: SWIFT message types vs on-chain

**Semana 11 — KYC Technology y Vendor Selection**
- E-KYC tools: digital identity, biometrics, facial recognition, geolocation
- Credit reference agencies, adverse media, beneficial ownership registers
- Network analysis tools: link analysis, criminality detection
- AI/ML en investigaciones: automatizacion de casos, open source tools
- Vendor selection criteria para AFC tools: integration, scalability, regulatory fit
- Data quality, taxonomy, access controls

**Checkpoint Fase 4:** quiz de 24 preguntas sobre Dominio D. Meta: 70%+ antes de avanzar.

---

### FASE 5 — Simulacro y Refuerzo
**Semanas 12-13 | Horas: 14**

- Semana 12: examen simulacro completo (120 preguntas, 3.5 horas cronometradas)
  - Si score < 75: identificar los 2 dominios con menor puntaje, volver a material especifico
  - Si score 75-82: refuerzo en preguntas incorrectas, segundo simulacro
  - Si score 83+: pasar a revision final
- Semana 13: revision de areas debiles, segundo simulacro si aplica, preparacion logistica del examen

---

## 3. Meta de fecha de examen

**Hoy:** 14 mayo 2026
**Semanas de estudio:** 13 semanas de contenido + 1 semana de buffer
**Fecha objetivo de examen: semana del 24 de agosto de 2026**

Calculo:
- 13 semanas de fases × 7 dias = 91 dias desde hoy
- 91 dias desde 14-may = ~13 de agosto
- +1 semana buffer para imprevistos = **examen target: 24-28 agosto 2026**
- Horas totales: 13 semanas × 5 dias habiles × 1 hora = 65 horas minimas. Agregar fines de semana parciales llega a ~90 horas — suficiente para base previa de Adrian.

**Tension identificada:** Adrian no tiene experiencia profesional remunerada (0 meses segun perfil). Para elegibilidad necesita 40 creditos. Con Associate of Science obtiene 10 creditos de educacion. Necesita 30 creditos adicionales — que puede cubrir con horas de training (1 credito/hora). El CAMS study package mismo otorga creditos. Esto debe resolverse ANTES de agendar el examen — ver Seccion 5.

---

## 4. Recursos disponibles en `/docs/`

Recurso confirmado en directorio:
- `/Users/your_username/Mis-Agentes/agente-CAMS/docs/CAMS Certification - Candidate Handbook - English.pdf`

Este handbook cubre: blueprint del examen (dominios A-D), politicas de elegibilidad, politicas del dia del examen, politicas de cancelacion/reprogramacion, y recertificacion.

**Recursos que Adrian debe adquirir via ACAMS al comprar el paquete:**
- Study Guide oficial CAMS (cubre los 4 dominios en profundidad)
- Flashcards ACAMS
- Practice exams via Enhanced Simulation Tool
- Dos cursos electivos incluidos en el paquete (AML sector case studies + regulatory framework de eleccion)

**Recomendacion de recurso electivo:** seleccionar "Virtual Assets / Crypto" como el framework de regulacion electivo — es el area donde Adrian ya tiene ventaja operativa y puede convertirla en puntos seguros.

---

## 5. Checklist de prereqs antes de agendar el examen

Los items marcados como [PENDIENTE] requieren accion inmediata — algunos tienen lead time de semanas.

### Elegibilidad (los 40 creditos)

- [ ] **[PENDIENTE] Confirmar creditos actuales en ACAMS.** Con Associate of Science = 10 creditos de educacion. Faltan 30.
- [ ] **[PENDIENTE] Calcular creditos de training.** El study package ACAMS otorga creditos por completar el learning path. Estimar cuantos cubre para saber si Adrian llega a 40 antes de agendar.
- [ ] **[PENDIENTE] Si faltan creditos:** agregar horas de training de fuentes externas — 1 credito por hora de training financiero relacionado (KYC, AML, sanctions). Chainalysis Academy (pendiente en perfil) puede contribuir aqui.
- [ ] Nota: sin experiencia profesional remunerada, Adrian no puede usar creditos de trabajo (10 creditos/año). Solo education + training.

### Membresia y aplicacion

- [ ] **[PENDIENTE — CRITICO] Activar membresia ACAMS.** Sin ella no se puede aplicar. Costo incluido en paquete o separado.
- [ ] **[PENDIENTE] Seleccionar y comprar paquete CAMS.** Standard (US$2,095 private) o con Virtual Classroom (US$2,495). Recomendacion: Virtual Classroom si el budget lo permite — el classroom genera creditos ACAMS adicionales hacia elegibilidad.
- [ ] Completar learning path del paquete (genera creditos automaticamente en perfil ACAMS).
- [ ] Verificar background verification — ACAMS se reserva el derecho de hacer criminal records check.
- [ ] Completar aplicacion online en acams.org una vez que creditos esten completos.
- [ ] Recibir Authorization to Test (ATT) por email de ACAMS.
- [ ] Agendar examen en Pearson VUE (online proctored disponible para US).

### Documentos para el dia del examen

- [ ] Dos formas de identificacion oficial vigente con foto y firma.
- [ ] Nombre en los IDs debe coincidir exactamente con nombre de registro en ACAMS.
- [ ] Si testa online: verificar requisitos tecnicos de Pearson VUE (camara, microfono, cuarto privado).

---

## 6. Estrategia para el dia del examen

Basada en politicas del handbook (Pearson VUE).

### Logistica pre-examen

- Llegar o loguearse 30 minutos antes de la hora agendada. Candidatos que llegan tarde pueden ser rechazados sin reembolso.
- Para examen presencial: dejar telefono, reloj, cartera y cualquier dispositivo electronico en el area segura ANTES de entrar. No llevar libros ni notas.
- Para examen online: cuarto privado, escritorio despejado, camara funcional. El proctor puede rechazar candidatos por irregularidades en el entorno.

### Estrategia dentro del examen (120 preguntas, 3.5 horas = 1 minuto 45 segundos por pregunta)

- **No dejar preguntas en blanco.** No hay penalidad por respuesta incorrecta. Responder todas, incluso si es una educated guess.
- **Primeras 2 semanas antes del examen:** practicar tiempo — completar bloques de 30 preguntas en 52 minutos cronometrados.
- **Cuando dudes:** eliminar 1-2 opciones claramente incorrectas primero, luego elegir entre las restantes. No cambiar respuesta a menos que hayas identificado un error especifico de lectura.
- **Flag y sigue:** si una pregunta requiere mas de 2 minutos, marcarla y continuar. Volver al final con el tiempo restante.
- **Pon atencion al lenguaje regulatorio:** CAMS usa terminos precisos — "must", "should", "may" tienen pesos diferentes. Leer enunciados completos antes de ver las opciones.

### Resultados

- Resultado se entrega inmediatamente al terminar el examen (pass/fail).
- Si no pasa en primer intento: retake disponible despues de 30 dias. Costo: US$299 (private). Identificar dominios debiles en los dias siguientes con base en el feedback.
- Resultado no se da por telefono ni email — solo en pantalla al terminar.

### Si necesitas cancelar o reprogramar

- Mas de 72 horas antes: sin costo via web, o US$20 por telefono.
- 24-72 horas antes: US$100 de penalidad.
- Menos de 24 horas o no-show: pierde el costo del examen completo, necesita nueva authorization de ACAMS (US$299).

---

## Proximos pasos inmediatos (esta semana)

1. **Hoy o manana:** ir a acams.org, activar membresia y revisar cuantos creditos de elegibilidad tienes actualmente.
2. **Esta semana:** comprar paquete CAMS y comenzar el learning path oficial.
3. **Semana 1 (14-21 mayo):** iniciar Fase 1, Semana 1 — Three Lines of Defense. Registrar sesion en `study_logs/` con formato: fecha, tema, tiempo, notas clave.
4. **Agendar examen en Pearson VUE** tan pronto ACAMS apruebe la aplicacion y envie ATT — apuntar a una fecha en la semana del 24 agosto 2026.

---

_Plan generado por agente-CAMS / Jarvis. Actualizar despues de cada checkpoint de fase con score real._
_Proxima revision recomendada: al completar Fase 1 (semana del 18 junio 2026)._
