import json
import logging
from datetime import date
from pathlib import Path

import anthropic
import config

logger = logging.getLogger(__name__)

PROFILE_PATH = Path(__file__).parent.parent / "mi_perfil.json"
PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_profile() -> dict:
    """Lee ../mi_perfil.json y retorna como dict."""
    try:
        return json.loads(PROFILE_PATH.read_text())
    except Exception as e:
        logger.error(f"load_profile failed: {e}")
        return {}


def generate_report(findings: list, mode: str, profile: dict) -> str:
    """
    Llama Claude API con los hallazgos y genera el reporte.
    mode: 'daily' o 'weekly'
    """
    # Load scout_profile for audit logging
    _scout_profile_path = Path(__file__).parent / "scout_profile.json"
    if _scout_profile_path.exists():
        import json as _json
        _sp = _json.loads(_scout_profile_path.read_text())
        logger.info(f"Scout profile: max_items={_sp.get('max_items', 5)}, priorities={len(_sp.get('prioridades', []))}, tags={list(_sp.get('tags', {}).keys())}")

    prompt_file = PROMPTS_DIR / f"{mode}_prompt.md"
    try:
        prompt_template = prompt_file.read_text()
    except Exception as e:
        logger.error(f"Could not read prompt file {prompt_file}: {e}")
        prompt_template = "Genera un reporte en español sobre estos hallazgos AI:\n\nHALLAZGOS:\n{findings}"

    prompt = prompt_template.format(
        profile=json.dumps(profile, indent=2, ensure_ascii=False),
        agents=", ".join(config.AGENTS),
        findings=json.dumps(findings, indent=2, ensure_ascii=False),
        date=date.today().strftime("%d %b %Y"),
    )

    try:
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=config.MODEL,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        report = message.content[0].text
        logger.info(f"analyzer: report generated ({len(report)} chars)")
        return report
    except Exception as e:
        logger.error(f"Claude API failed: {e}")
        # Fallback: retorna hallazgos crudos
        lines = [f"Scout Report — {date.today().strftime('%d %b %Y')}", "", "(Error al generar análisis con Claude)", ""]
        for f in findings[:10]:
            lines.append(f"• {f.get('title', 'Sin título')}")
            lines.append(f"  {f.get('url', '')}")
            lines.append("")
        return "\n".join(lines)
