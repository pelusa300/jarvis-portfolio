#!/usr/bin/env python3
"""
Example: seed the applications tracker with fake data.
Run once to populate a demo DB for testing.
Usage: python3 -m tracker.seed_example
"""
from tracker.db import init_db, add_application

FAKE_APPS = [
    {
        "company": "Acme Crypto",
        "title": "AML Analyst",
        "url": "https://example.com/jobs/aml-analyst",
        "source": "remoteok",
        "status": "aplicada",
        "date_applied": "2026-10-20",
    },
    {
        "company": "BlockFinance",
        "title": "Compliance Officer",
        "url": "https://example.com/jobs/compliance-officer",
        "source": "linkedin",
        "status": "entrevista",
        "date_applied": "2026-10-15",
        "notes": "Segunda entrevista programada",
    },
    {
        "company": "OldCoin Inc",
        "title": "KYC Specialist",
        "url": "https://example.com/jobs/kyc-specialist",
        "source": "web3career",
        "status": "cerrada",
    },
    {
        "company": "DeFiCorp",
        "title": "RegTech Analyst",
        "url": "https://example.com/jobs/regtech-analyst",
        "source": "greenhouse",
        "status": "por aplicar",
        "no_reapply_until": "2027-04-01",
    },
]

if __name__ == "__main__":
    init_db()
    for app in FAKE_APPS:
        id_ = add_application(**app)
        print(f"  #{id_} {app['title']} — {app['company']} [{app['status']}]")
    print(f"\nSeed complete: {len(FAKE_APPS)} applications added.")
