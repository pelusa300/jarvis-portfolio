#!/usr/bin/env python3
"""
apply.py — CLI para el tracker de aplicaciones.

Uso:
  python3 apply.py add [--company X] [--title Y] [--url Z] [--status S]
                       [--date-applied D] [--notes N] [--no-reapply-until D]
  python3 apply.py add --from-report N          # job #N del reporte diario
  python3 apply.py update <id> [--status S] [--next-step N] [--follow-up-date D]
                               [--notes N] [--no-reapply-until U] [--date-applied D]
  python3 apply.py list [--status S]
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tracker.db import (
    init_db, add_application, update_application,
    list_applications, get_application, VALID_STATUSES,
)

_REPORT_JSON = Path(__file__).parent.parent / "shared_reports" / "job_market_latest.json"


def _pick_from_report(n: int) -> dict:
    if not _REPORT_JSON.exists():
        print(f"❌ No encontrado: {_REPORT_JSON}")
        sys.exit(1)
    data = json.loads(_REPORT_JSON.read_text(encoding="utf-8"))
    all_jobs = data.get("strict", []) + data.get("broad", [])
    if n < 1 or n > len(all_jobs):
        print(f"❌ El reporte tiene {len(all_jobs)} vacantes; --from-report debe ser 1–{len(all_jobs)}.")
        sys.exit(1)
    return all_jobs[n - 1]


def cmd_add(args):
    init_db()

    if args.from_report is not None:
        job = _pick_from_report(args.from_report)
        company = job.get("company", "")
        title = job.get("title", "")
        url = job.get("url")
        source = job.get("source")
        print(f"Vacante #{args.from_report}: {title} — {company}")
    else:
        if args.company and args.title:
            # Modo flags: no prompts
            company = args.company
            title = args.title
            url = args.url
            source = args.source
        else:
            # Modo interactivo: pedir los campos que falten
            company = args.company or input("Empresa: ").strip()
            title = args.title or input("Puesto: ").strip()
            url = args.url or input("URL (Enter para omitir): ").strip() or None
            source = args.source or None

    if not company or not title:
        print("❌ Empresa y puesto son obligatorios.")
        sys.exit(1)

    id_ = add_application(
        company=company,
        title=title,
        url=url,
        source=source,
        date_applied=args.date_applied,
        status=args.status or "por aplicar",
        notes=args.notes,
        no_reapply_until=args.no_reapply_until,
    )
    print(f"✅ Aplicación #{id_} añadida: {title} — {company} [{args.status or 'por aplicar'}]")


def cmd_update(args):
    init_db()
    app = get_application(args.id)
    if not app:
        print(f"❌ No encontrada aplicación #{args.id}")
        sys.exit(1)

    kwargs = {}
    if args.status:
        kwargs["status"] = args.status
    if args.next_step:
        kwargs["next_step"] = args.next_step
    if args.follow_up_date:
        kwargs["follow_up_date"] = args.follow_up_date
    if args.notes:
        kwargs["notes"] = args.notes
    if args.no_reapply_until:
        kwargs["no_reapply_until"] = args.no_reapply_until
    if args.date_applied:
        kwargs["date_applied"] = args.date_applied

    if not kwargs:
        print("⚠️  Ningún campo para actualizar. Usa --status, --next-step, etc.")
        sys.exit(0)

    update_application(args.id, **kwargs)
    print(f"✅ Aplicación #{args.id} ({app['title']} — {app['company']}) actualizada:")
    for k, v in kwargs.items():
        print(f"   {k}: {v}")


def cmd_list(args):
    init_db()
    apps = list_applications(status=args.status or None)
    if not apps:
        msg = f"No hay aplicaciones con status '{args.status}'." if args.status else "No hay aplicaciones registradas."
        print(msg)
        return

    print(f"\n{'#':<4} {'Empresa':<22} {'Puesto':<36} {'Estado':<15} {'Aplicada':<12} {'Seguimiento'}")
    print("─" * 105)
    for a in apps:
        stale_flag = " ⚠️" if _is_stale(a.get("date_found")) else ""
        print(
            f"{a['id']:<4} "
            f"{(a['company'] or '')[:21]:<22} "
            f"{(a['title'] or '')[:35]:<36} "
            f"{(a['status'] or '')[:14]:<15} "
            f"{(a['date_applied'] or '—'):<12} "
            f"{a.get('follow_up_date') or '—'}"
            f"{stale_flag}"
        )
    print(f"\nTotal: {len(apps)}")


def _is_stale(date_found):
    if not date_found:
        return False
    try:
        from datetime import timedelta
        return (date.today() - date.fromisoformat(date_found)).days > 21
    except ValueError:
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Job Application Tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── add ──────────────────────────────────────────────────────────────
    add_p = sub.add_parser("add", help="Añadir aplicación")
    add_p.add_argument("--from-report", type=int, metavar="N",
                       help="Añadir vacante #N del reporte diario (job_market_latest.json)")
    add_p.add_argument("--company")
    add_p.add_argument("--title")
    add_p.add_argument("--url")
    add_p.add_argument("--source")
    add_p.add_argument("--status", choices=sorted(VALID_STATUSES), default="por aplicar")
    add_p.add_argument("--date-applied", dest="date_applied",
                       help="Fecha ISO (ej. 2026-10-26)")
    add_p.add_argument("--notes")
    add_p.add_argument("--no-reapply-until", dest="no_reapply_until",
                       help="Fecha ISO. Bloquea que el scraper recomiende esta empresa hasta esa fecha.")

    # ── update ───────────────────────────────────────────────────────────
    upd_p = sub.add_parser("update", help="Actualizar aplicación por ID")
    upd_p.add_argument("id", type=int, help="ID de la aplicación")
    upd_p.add_argument("--status", choices=sorted(VALID_STATUSES))
    upd_p.add_argument("--next-step", dest="next_step")
    upd_p.add_argument("--follow-up-date", dest="follow_up_date",
                       help="Fecha ISO del próximo seguimiento")
    upd_p.add_argument("--notes")
    upd_p.add_argument("--no-reapply-until", dest="no_reapply_until",
                       help="Fecha ISO hasta la que no reaplicar")
    upd_p.add_argument("--date-applied", dest="date_applied")

    # ── list ─────────────────────────────────────────────────────────────
    lst_p = sub.add_parser("list", help="Listar aplicaciones")
    lst_p.add_argument("--status", choices=sorted(VALID_STATUSES),
                       help="Filtrar por status")

    args = parser.parse_args()

    if args.command == "add":
        cmd_add(args)
    elif args.command == "update":
        cmd_update(args)
    elif args.command == "list":
        cmd_list(args)


if __name__ == "__main__":
    main()
