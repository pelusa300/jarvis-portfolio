"""
Descarga el SDN Advanced XML de OFAC, extrae todas las direcciones de
criptomonedas y actualiza la base de datos local.

Seguridad ante fallos:
- Si la descarga falla              → no toca la DB, registra el error
- Si el XML no parsea               → no toca la DB, registra el error
- Si se extraen 0 direcciones       → no toca la DB, registra el error
- Si el resultado es < 50% del prev → no toca la DB, registra el error
En todos los casos de fallo el reporte y sync_log reflejan la falla,
y el health-check la detecta por el timestamp del reporte.
"""
import logging
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).parent
LOG_PATH = BASE / "logs" / "sync.log"
LOG_PATH.parent.mkdir(exist_ok=True)
# Single cached copy of the XML — overwritten on every sync, never accumulates
XML_CACHE = BASE / "ofac_data" / "sdn_advanced.xml"
XML_CACHE.parent.mkdir(exist_ok=True)

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

SDN_URL = (
    "https://sanctionslistservice.ofac.treas.gov"
    "/api/publicationpreview/exports/sdn_advanced.xml"
)
# Namespace used in sdn_advanced.xml
NS_URI = (
    "https://sanctionslistservice.ofac.treas.gov"
    "/api/PublicationPreview/exports/ADVANCED_XML"
)

SHARED_REPORTS = BASE.parent / "shared_reports"


def _ns(tag: str) -> str:
    return f"{{{NS_URI}}}{tag}"


def _download_xml() -> bytes:
    req = urllib.request.Request(
        SDN_URL,
        headers={"User-Agent": "Jarvis OFAC Sync/1.0 (compliance screening tool)"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def _parse_crypto_feature_type_ids(root: ET.Element) -> dict[str, str]:
    """
    Dynamically extract {feature_type_id: currency} from ReferenceValueSets,
    for all FeatureType names starting with 'Digital Currency Address - '.
    This avoids hardcoding IDs that OFAC could change in a schema update.
    """
    mapping = {}
    ref_sets = root.find(_ns("ReferenceValueSets"))
    if ref_sets is None:
        return mapping
    ft_values = ref_sets.find(_ns("FeatureTypeValues"))
    if ft_values is None:
        return mapping
    prefix = "Digital Currency Address - "
    for item in ft_values:
        text = (item.text or "").strip()
        if text.startswith(prefix):
            currency = text[len(prefix):]
            mapping[item.get("ID")] = currency
    return mapping


def _parse_list_date(root: ET.Element) -> str:
    doi = root.find(_ns("DateOfIssue"))
    if doi is None:
        return "unknown"
    y = getattr(doi.find(_ns("Year")), "text", "")
    m = getattr(doi.find(_ns("Month")), "text", "")
    d = getattr(doi.find(_ns("Day")), "text", "")
    try:
        return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    except (TypeError, ValueError):
        return "unknown"


def _extract_records(root: ET.Element, crypto_ids: dict[str, str], list_date: str) -> list[dict]:
    """
    Walk DistinctParties and extract one record per (address, currency, entity).
    The address value is the text of the first VersionDetail with non-empty text
    inside a Feature whose FeatureTypeID is in crypto_ids.
    """
    records = []
    distinct_parties = root.find(_ns("DistinctParties"))
    if distinct_parties is None:
        return records

    for party in distinct_parties:
        fixed_ref = party.get("FixedRef", "")

        # Primary entity name: Identity[@Primary='true'] →
        #   Alias[@Primary='true'] → DocumentedName[@DocNameStatusID='1'] →
        #   NamePartValue texts joined
        entity_name = ""
        for profile in party.findall(_ns("Profile")):
            for identity in profile.findall(_ns("Identity")):
                if identity.get("Primary") != "true":
                    continue
                for alias in identity.findall(_ns("Alias")):
                    if alias.get("Primary") != "true":
                        continue
                    for doc_name in alias.findall(_ns("DocumentedName")):
                        if doc_name.get("DocNameStatusID") != "1":
                            continue
                        parts = [
                            nv.text
                            for nv in doc_name.findall(f".//{_ns('NamePartValue')}")
                            if nv.text
                        ]
                        entity_name = " ".join(parts).strip()
                        break
                    if entity_name:
                        break
                if entity_name:
                    break

            # Crypto features
            for feature in profile.findall(_ns("Feature")):
                ftype_id = feature.get("FeatureTypeID", "")
                if ftype_id not in crypto_ids:
                    continue
                currency = crypto_ids[ftype_id]
                for fv in feature.findall(_ns("FeatureVersion")):
                    for vd in fv.findall(_ns("VersionDetail")):
                        addr = (vd.text or "").strip()
                        if addr:
                            records.append({
                                "address": addr,
                                "currency": currency,
                                "entity_name": entity_name or "UNKNOWN",
                                "entity_id": fixed_ref,
                                "list_date": list_date,
                            })
                            break  # one address per FeatureVersion

    return records


def _write_report(status: str, list_date: str, total: int,
                  added: int, removed: int,
                  currency_counts: dict, error_msg: str = "") -> None:
    SHARED_REPORTS.mkdir(exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    # status field on the metadata line lets health-check detect FAIL immediately
    # without waiting for a stale timestamp
    status_meta = "OK" if not error_msg else f"FAIL — {error_msg[:80]}"
    lines = [
        "# OFAC Crypto Screening — Sync Status",
        f"_updated: {now} | owner: agente-ofac | frequency: daily | status: {status_meta}_",
        "",
        f"**List date:** {list_date}",
        f"**Total addresses indexed:** {total:,}",
        f"**Last sync changes:** +{added} added, -{removed} removed",
        "",
    ]
    if currency_counts:
        lines.append("**Breakdown by currency:**")
        for cur, count in sorted(currency_counts.items(), key=lambda x: -x[1]):
            lines.append(f"- {cur}: {count:,}")
        lines.append("")
    if error_msg:
        lines.append(f"**Error:** {error_msg}")
        lines.append("")
    (SHARED_REPORTS / "ofac_latest.md").write_text("\n".join(lines))


def run() -> int:
    """Returns 0 on success, 1 on failure."""
    import ofac_db

    ofac_db.init_db()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    prev_total = ofac_db.total_count()

    # --- Download ---
    log.info("Downloading SDN Advanced XML from OFAC...")
    try:
        xml_bytes = _download_xml()
    except Exception as exc:
        msg = f"Download failed: {exc}"
        log.error(msg)
        ofac_db.log_sync(now_str, "unknown", prev_total, 0, 0, error=msg)
        _write_report("FAILED", "unknown", prev_total, 0, 0, {}, error_msg=msg)
        return 1

    # Save single cached copy (overwrites previous — no accumulation)
    XML_CACHE.write_bytes(xml_bytes)
    log.info(f"XML saved to {XML_CACHE}")

    # --- Parse ---
    log.info(f"Parsing XML ({len(xml_bytes):,} bytes)...")
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        msg = f"XML parse error: {exc}"
        log.error(msg)
        ofac_db.log_sync(now_str, "unknown", prev_total, 0, 0, error=msg)
        _write_report("FAILED", "unknown", prev_total, 0, 0, {}, error_msg=msg)
        return 1

    list_date = _parse_list_date(root)
    crypto_ids = _parse_crypto_feature_type_ids(root)
    log.info(f"List date: {list_date} | Crypto feature types found: {len(crypto_ids)}")

    # --- Extract ---
    records = _extract_records(root, crypto_ids, list_date)
    log.info(f"Extracted {len(records)} crypto address records")

    # --- Safety checks ---
    if len(records) == 0:
        msg = "Extracted 0 addresses — parser may be broken or schema changed"
        log.error(msg)
        ofac_db.log_sync(now_str, list_date, prev_total, 0, 0, error=msg)
        _write_report("FAILED", list_date, prev_total, 0, 0, {}, error_msg=msg)
        return 1

    if prev_total > 0 and len(records) < prev_total * 0.5:
        msg = (
            f"Extracted {len(records)} addresses but DB has {prev_total} — "
            f"less than 50% of previous count, aborting to preserve existing data"
        )
        log.error(msg)
        ofac_db.log_sync(now_str, list_date, prev_total, 0, 0, error=msg)
        _write_report("FAILED", list_date, prev_total, 0, 0, {}, error_msg=msg)
        return 1

    # --- Update DB ---
    added, removed = ofac_db.replace_all(records)
    total = ofac_db.total_count()
    cur_counts = ofac_db.currency_counts()
    ofac_db.log_sync(now_str, list_date, total, added, removed)

    log.info(f"Sync complete — total={total}, +{added} added, -{removed} removed")
    _write_report("OK", list_date, total, added, removed, cur_counts)
    return 0


if __name__ == "__main__":
    sys.exit(run())
