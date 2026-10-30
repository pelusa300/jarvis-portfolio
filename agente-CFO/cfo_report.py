#!/usr/bin/env python3
"""CFO Report — reporte financiero semanal de Adrian Ontiveros."""
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
FINANZAS_PATH = BASE_DIR / "finanzas.json"
FLARE_PATH = BASE_DIR / "agente-flare" / "flare_live_data.json"
XRP_JOURNAL_PATH = BASE_DIR / "agente-crypto" / "swing_journal.md"
LOG_DIR = Path(__file__).parent / "logs"
ENV_PATH = BASE_DIR / "agente-finanzas" / ".env"

COLCHON = 1000.0
FINANZAS_THREAD_ID = int(os.getenv("TELEGRAM_THREAD_FINANZAS", "0"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)


def load_finanzas() -> dict:
    with open(FINANZAS_PATH) as f:
        return json.load(f)


def load_flare() -> dict:
    with open(FLARE_PATH) as f:
        data = json.load(f)
    return data.get("my_pools", {})


def load_xrp_lab() -> dict:
    text = XRP_JOURNAL_PATH.read_text()
    capital_match = re.search(r"Capital total swing:\*?\*?\s*\$([0-9,]+\.?\d*)", text)
    capital = float(capital_match.group(1).replace(",", "")) if capital_match else 0.0
    activo = bool(re.search(r'CICLO\s+\d+', text)) and not bool(
        re.search(r'CICLO.*completado|##.*CICLO.*Fin', text, re.IGNORECASE)
    )
    return {"capital": capital, "activo": activo}


def checking_emoji(checking: float) -> str:
    if checking >= 3000:
        return "✅"
    if checking >= 1500:
        return "🟡"
    return "🔴"


def calcular_situacion(finanzas: dict) -> dict:
    checking = finanzas["liquidez"]["checking"]
    deuda_total = finanzas["deudas"]["total"]
    ingreso = finanzas["ingresos"]["promedio_mensual"]
    gastos = finanzas["gastos_fijos"]["total"]
    flujo_libre = ingreso - gastos

    excedente = max(0.0, checking - COLCHON)
    puede_pagar_deuda = deuda_total > 0 and excedente >= deuda_total

    deuda_detalle = {
        k: v for k, v in finanzas["deudas"].items()
        if k != "total" and isinstance(v, (int, float)) and v > 0
    }

    planeados = finanzas.get("gastos_planeados", {})
    meta_resort = sum(
        v.get("monto", 0) for v in planeados.values()
        if isinstance(v, dict) and "tarjeta" in v
    )
    vuelo_restante = sum(
        v.get("restante", 0) for v in planeados.values()
        if isinstance(v, dict) and "cuota_mensual" in v
    )

    return {
        "checking": checking,
        "flujo_libre": flujo_libre,
        "deuda_total": deuda_total,
        "deuda_detalle": deuda_detalle,
        "excedente": excedente,
        "puede_pagar_deuda": puede_pagar_deuda,
        "meta_resort": meta_resort,
        "vuelo_restante": vuelo_restante,
    }


def build_message(situacion: dict) -> str:
    hoy = datetime.now().strftime("%d %b %Y")
    checking = situacion["checking"]
    flujo = situacion["flujo_libre"]
    deuda = situacion["deuda_total"]
    excedente = situacion["excedente"]
    puede_pagar = situacion["puede_pagar_deuda"]
    detalle = situacion["deuda_detalle"]
    pools = situacion.get("flare_pools", {})
    xrp = situacion.get("xrp_lab", {})
    meta_resort = situacion.get("meta_resort", 0)
    vuelo_restante = situacion.get("vuelo_restante", 0)

    emoji = checking_emoji(checking)

    lines = [
        f"📊 *CFO REPORT — {hoy}*",
        "",
        "💰 SITUACIÓN",
        f"  Checking:     ${checking:,.0f}  {emoji}",
        f"  Flujo libre:  ${flujo:,.2f}/mes",
    ]

    if deuda > 0:
        detalle_str = " + ".join(f"{k.replace('_', ' ').title()} ${v:,.0f}" for k, v in detalle.items())
        deuda_line = f"  Deuda:        ${deuda:,.0f}  🔴"
        if detalle_str:
            deuda_line += f" ({detalle_str})"
        lines.append(deuda_line)
    else:
        lines.append("  Deuda:        $0  ✅ Sin deuda")

    lines.append("")
    lines.append("⚡ FLARE")
    if pools:
        for nombre, datos in pools.items():
            apy = datos.get("apy", 0)
            lines.append(f"  {nombre}: {apy:.2f}% APY")
    else:
        lines.append("  Sin datos de pools disponibles")

    lines.append("")
    lines.append("🔬 LAB XRP")
    estado = "activo" if xrp.get("activo") else "inactivo"
    lines.append(f"  Capital: ${xrp.get('capital', 0):,.2f}  |  Estado: {estado}")

    if meta_resort > 0 or vuelo_restante > 0:
        lines.append("")
        lines.append("✈️ PUNTA CANA")
        if meta_resort > 0:
            lines.append(f"  Resort: ${meta_resort:,.0f} (cargo pendiente a tarjeta)")
        if vuelo_restante > 0:
            lines.append(f"  Vuelo: ${vuelo_restante:,.0f} restantes ($113/mes)")
        meta_total = meta_resort + vuelo_restante
        lines.append(f"  Meta total: ${meta_total:,.0f}")

    lines.append("")
    lines.append("📌 ACCIÓN RECOMENDADA")

    if deuda > 0 and puede_pagar and detalle:
        deuda_mayor = max(detalle.items(), key=lambda x: x[1])
        lines.append(f"  Puedes liquidar {deuda_mayor[0].replace('_', ' ').title()} (${deuda_mayor[1]:,.0f}) hoy.")
        lines.append(f"  Tienes excedente de ${excedente:,.0f} sobre tu colchón.")
    elif deuda > 0 and puede_pagar:
        lines.append(f"  Puedes liquidar la deuda total (${deuda:,.0f}) hoy.")
        lines.append(f"  Tienes excedente de ${excedente:,.0f} sobre tu colchón.")
    elif deuda > 0:
        lines.append(f"  Liquidar deuda (${deuda:,.0f}) mañana. Luego modo acumulación.")
    elif meta_resort > 0:
        faltan = max(0.0, meta_resort - excedente)
        if faltan > 0:
            lines.append(f"  Acumulando para resort Punta Cana. Meta: ${meta_resort:,.0f}.")
            lines.append(f"  Guardado: ${excedente:,.0f}  |  Faltan: ${faltan:,.0f}")
        else:
            lines.append(f"  ✅ Ya tienes cubierto el resort (${meta_resort:,.0f}). Listo para cargar a tarjeta.")
    else:
        lines.append(f"  Sin deudas ni metas pendientes. Excedente: ${excedente:,.0f}")

    return "\n".join(lines)


def send_telegram(message: str, token: str, chat_id: str, message_thread_id: int = None) -> tuple[bool, str]:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    if message_thread_id:
        payload["message_thread_id"] = message_thread_id
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("Telegram enviado OK")
        return True, ""
    except requests.RequestException as e:
        error_msg = f"{e}"
        if hasattr(e, "response") and e.response is not None:
            error_msg = f"HTTP {e.response.status_code} — {e.response.text}"
        logger.error("Error enviando Telegram: %s", error_msg)
        return False, error_msg


def _send_with_fallback(message: str, token: str, group_id: str, dm_id: str) -> bool:
    if group_id:
        ok, err = send_telegram(message, token, group_id, FINANZAS_THREAD_ID)
        if ok:
            return True
        logger.warning("Envío al grupo falló, usando DM como respaldo: %s", err)
    ok, _ = send_telegram(message, token, dm_id)
    return ok


def write_log(message: str) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    log_file = LOG_DIR / f"cfo_{datetime.now().strftime('%Y-%m-%d')}.log"
    with open(log_file, "a") as f:
        f.write(f"[{datetime.now().isoformat()}]\n{message}\n\n")


def main() -> None:
    load_dotenv(Path.home() / ".config/jarvis/.env")  # API key central
    load_dotenv(ENV_PATH)                              # vars locales del agente
    token = os.environ.get("TELEGRAM_FINANCE_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    group_id = os.environ.get("TELEGRAM_GROUP_ID")

    if not token or not chat_id:
        logger.error("Faltan TELEGRAM_FINANCE_BOT_TOKEN o TELEGRAM_CHAT_ID")
        sys.exit(1)

    logger.info("Cargando datos...")
    try:
        finanzas = load_finanzas()
        flare_pools = load_flare()
        xrp_lab = load_xrp_lab()
        situacion = calcular_situacion(finanzas)
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        logger.error("Error cargando datos: %s", e)
        _send_with_fallback(f"⚠️ CFO ERROR: no se pudo generar el reporte.\n{e}", token, group_id, chat_id)
        sys.exit(1)
    situacion["flare_pools"] = flare_pools
    situacion["xrp_lab"] = xrp_lab

    mensaje = build_message(situacion)
    logger.info("Mensaje construido:\n%s", mensaje)

    success = _send_with_fallback(mensaje, token, group_id, chat_id)
    write_log(f"STATUS: {'OK' if success else 'TELEGRAM_FAILED'}\n\n{mensaje}")


if __name__ == "__main__":
    main()
