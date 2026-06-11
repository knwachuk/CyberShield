#!/usr/bin/env python3
"""Command-line interface exercising all three CyberShield engines.

Examples
--------
Collect an account and its posts (Social Data Analytics engine)::

    python cli.py collect kind_amy

Compare two accounts for directed abuse (Cyber Shield engine)::

    python cli.py shield abuser_joe kind_amy

Reconcile a cross-platform identity from the bundled sample (Identity engine)::

    python cli.py reconcile

All commands fall back to bundled sample data when no live API credentials are
configured, so the CLI is runnable out of the box.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cybershield.config import settings
from cybershield.engines.cyber_shield import CyberShieldEngine
from cybershield.engines.cyber_shield.analyzers import AbuseAnalyzer
from cybershield.engines.identity_reconciliation import (
    CyberIdentityReconciliationEngine,
)
from cybershield.engines.social_analytics import SocialDataAnalyticsEngine
from cybershield.models import Account, Platform


def _print(obj) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def cmd_collect(args: argparse.Namespace) -> None:
    engine = SocialDataAnalyticsEngine.with_defaults()
    result = engine.collect(Platform.TWITTER, args.username, post_limit=args.limit)
    _print(
        {
            "account": result["account"].to_dict(),
            "post_count": len(result["posts"]),
            "analytics": result["analytics"],
        }
    )


def cmd_shield(args: argparse.Namespace) -> None:
    data_engine = SocialDataAnalyticsEngine.with_defaults()
    shield = CyberShieldEngine(analyzer=AbuseAnalyzer(full_mode=settings.is_full_mode))
    report = shield.compare_via_engine(
        data_engine,
        Platform.TWITTER,
        args.account_a,
        args.account_b,
        post_limit=args.limit,
        bidirectional=not args.one_way,
    )
    print(report.summary())
    print("-" * 60)
    _print(report.to_dict())


def cmd_reconcile(args: argparse.Namespace) -> None:
    path = Path(args.fixture or (settings.data_dir / "sample_identity.json"))
    payload = json.loads(path.read_text(encoding="utf-8"))
    source = Account.from_dict(payload["source"])
    candidates = [Account.from_dict(c) for c in payload["candidates"]]

    engine = CyberIdentityReconciliationEngine()
    results = engine.reconcile(source, candidates)
    print(f"Source: {source.handle}\n")
    for result in results:
        print(result.explain())
        print()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CyberShield command-line interface.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_collect = sub.add_parser("collect", help="Collect an account + posts.")
    p_collect.add_argument("username")
    p_collect.add_argument("--limit", type=int, default=100)
    p_collect.set_defaults(func=cmd_collect)

    p_shield = sub.add_parser("shield", help="Compare two accounts for abuse.")
    p_shield.add_argument("account_a")
    p_shield.add_argument("account_b")
    p_shield.add_argument("--limit", type=int, default=100)
    p_shield.add_argument("--one-way", action="store_true",
                          help="Only assess A→B (skip the reverse direction).")
    p_shield.set_defaults(func=cmd_shield)

    p_rec = sub.add_parser("reconcile", help="Cross-platform identity match demo.")
    p_rec.add_argument("--fixture", help="Path to an identity fixture JSON.")
    p_rec.set_defaults(func=cmd_reconcile)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
