import json
import sys
from pathlib import Path
from unittest.mock import patch, mock_open

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


# ── Tests de calcular_situacion ──────────────────────────────────────────────

def test_excedente_sobre_colchon():
    from cfo_report import calcular_situacion
    finanzas = {"liquidez": {"checking": 2500}, "deudas": {"total": 0}, "ingresos": {"promedio_mensual": 3200}, "gastos_fijos": {"total": 1261.65}}
    resultado = calcular_situacion(finanzas)
    assert resultado["excedente"] == 2500 - 1000  # checking - colchon

def test_excedente_cero_cuando_checking_bajo():
    from cfo_report import calcular_situacion
    finanzas = {"liquidez": {"checking": 800}, "deudas": {"total": 200}, "ingresos": {"promedio_mensual": 3200}, "gastos_fijos": {"total": 1261.65}}
    resultado = calcular_situacion(finanzas)
    assert resultado["excedente"] == 0

def test_flujo_libre():
    from cfo_report import calcular_situacion
    finanzas = {"liquidez": {"checking": 2000}, "deudas": {"total": 500}, "ingresos": {"promedio_mensual": 3200}, "gastos_fijos": {"total": 1200}}
    resultado = calcular_situacion(finanzas)
    assert resultado["flujo_libre"] == 3200 - 1200

def test_puede_pagar_deuda_completa_cuando_hay_margen():
    from cfo_report import calcular_situacion
    finanzas = {"liquidez": {"checking": 3000}, "deudas": {"total": 500, "gemini_card": 500, "amex_gold": 0}, "ingresos": {"promedio_mensual": 3200}, "gastos_fijos": {"total": 1200}}
    resultado = calcular_situacion(finanzas)
    # checking $3000 - colchon $1000 = $2000 excedente, deuda $500 -> puede pagar
    assert resultado["puede_pagar_deuda"] is True

def test_no_puede_pagar_deuda_cuando_no_hay_margen():
    from cfo_report import calcular_situacion
    finanzas = {"liquidez": {"checking": 1200}, "deudas": {"total": 962}, "ingresos": {"promedio_mensual": 3200}, "gastos_fijos": {"total": 1200}}
    resultado = calcular_situacion(finanzas)
    # checking $1200 - colchon $1000 = $200 excedente, deuda $962 -> no puede pagar
    assert resultado["puede_pagar_deuda"] is False


# ── Tests de checking_emoji ──────────────────────────────────────────────────

def test_emoji_rojo_bajo_1500():
    from cfo_report import checking_emoji
    assert checking_emoji(900) == "🔴"
    assert checking_emoji(1499) == "🔴"

def test_emoji_amarillo_entre_1500_y_3000():
    from cfo_report import checking_emoji
    assert checking_emoji(1500) == "🟡"
    assert checking_emoji(2999) == "🟡"

def test_emoji_verde_sobre_3000():
    from cfo_report import checking_emoji
    assert checking_emoji(3000) == "✅"
    assert checking_emoji(10000) == "✅"


# ── Tests de build_message ───────────────────────────────────────────────────

def test_mensaje_contiene_seccion_situacion():
    from cfo_report import build_message
    situacion = {
        "checking": 1280, "flujo_libre": 1938.35, "deuda_total": 962,
        "deuda_detalle": {"gemini_card": 518, "amex_gold": 444},
        "excedente": 280, "puede_pagar_deuda": False,
        "flare_pools": {"stXRP/FXRP LP": {"apy": 1.27}, "sFLR/WFLR LP": {"apy": 11.08}},
        "xrp_lab": {"capital": 848.06, "activo": True}
    }
    msg = build_message(situacion)
    assert "💰 SITUACIÓN" in msg
    assert "⚡ FLARE" in msg
    assert "🔬 LAB XRP" in msg
    assert "📌 ACCIÓN" in msg

def test_mensaje_recomienda_pagar_cuando_puede():
    from cfo_report import build_message
    situacion = {
        "checking": 3000, "flujo_libre": 1938.35, "deuda_total": 500,
        "deuda_detalle": {"gemini_card": 500, "amex_gold": 0},
        "excedente": 2000, "puede_pagar_deuda": True,
        "flare_pools": {},
        "xrp_lab": {"capital": 848.06, "activo": True}
    }
    msg = build_message(situacion)
    assert "liquidar" in msg.lower() or "pagar" in msg.lower()

def test_mensaje_sin_deuda_no_menciona_pagar():
    from cfo_report import build_message
    situacion = {
        "checking": 5000, "flujo_libre": 1938.35, "deuda_total": 0,
        "deuda_detalle": {},
        "excedente": 4000, "puede_pagar_deuda": False,
        "flare_pools": {"sFLR/WFLR LP": {"apy": 11.08}},
        "xrp_lab": {"capital": 848.06, "activo": True}
    }
    msg = build_message(situacion)
    assert "deuda" not in msg.lower() or "sin deuda" in msg.lower()
