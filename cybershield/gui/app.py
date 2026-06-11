"""Flask application that puts a friendly face on the Cyber Shield engine.

The whole UI is intentionally a single file: a couple of routes plus one inline
HTML template rendered with ``render_template_string``. That keeps the GUI easy
to read, copy and run without juggling a templates/ directory, while still using
real server-side rendering rather than hand-built HTML strings everywhere.

The app talks only to the high-level engines (``SocialDataAnalyticsEngine`` and
``CyberShieldEngine``), so it stays decoupled from connector and analyzer
internals.
"""

from __future__ import annotations

from cybershield.config import settings
from cybershield.engines.cyber_shield import CyberShieldEngine
from cybershield.engines.cyber_shield.analyzers import AbuseAnalyzer
from cybershield.engines.cyber_shield.embedding import embed_2d
from cybershield.engines.social_analytics import SocialDataAnalyticsEngine
from cybershield.models import Platform


def _score_color(score: float) -> str:
    """Interpolate a fill colour from green (clean) through amber to red (abuse)."""
    green, amber, red = (0x2f, 0xbf, 0x71), (0xf5, 0xa6, 0x23), (0xe0, 0x53, 0x3d)
    if score < 0.5:
        a, b, t = green, amber, score / 0.5
    else:
        a, b, t = amber, red, (score - 0.5) / 0.5
    rgb = [round(a[i] + (b[i] - a[i]) * t) for i in range(3)]
    return "#%02x%02x%02x" % tuple(rgb)


def _conversation_points(report) -> list[dict]:
    """Turn every directed message in the report into a plottable point.

    Both directions are embedded together so the scatter shows the whole
    conversation in one space. Each point carries the metadata the SVG needs:
    position, colour (by abuse score), marker shape (by direction) and a tooltip.
    """
    directions = [("a_to_b", report.a_to_b)]
    if report.b_to_a is not None:
        directions.append(("b_to_a", report.b_to_a))

    records = []
    for key, direction in directions:
        label = f"{direction.from_account.username} → {direction.to_account.username}"
        for assessment in direction.assessments:
            records.append((key, label, assessment))

    coords = embed_2d([a.text for _, _, a in records])

    points = []
    for (key, label, assessment), (x, y) in zip(records, coords):
        points.append(
            {
                "x": round(x * 100, 2),
                "y": round((1 - y) * 100, 2),  # flip so higher y is visually up
                "abuse_score": round(assessment.abuse_score, 2),
                "is_abusive": assessment.is_abusive,
                "sentiment": assessment.sentiment,
                "direction": key,
                "direction_label": label,
                "shape": "circle" if key == "a_to_b" else "rect",
                "fill": _score_color(assessment.abuse_score),
                "text": assessment.text,
            }
        )
    return points


def create_app():
    """Application factory. Returns a configured Flask app.

    Flask is imported here (not at module top) so importing the package never
    hard-requires Flask — only launching the GUI does.
    """
    try:
        from flask import Flask, render_template_string, request
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "Flask is required to run the GUI. Install it with "
            "'pip install flask' (or 'pip install -r requirements.txt')."
        ) from exc

    app = Flask(__name__)

    # Engines are built once and reused across requests. The analyzer mode is
    # driven by configuration (lite by default; full pulls in transformers).
    data_engine = SocialDataAnalyticsEngine.with_defaults()
    shield = CyberShieldEngine(
        analyzer=AbuseAnalyzer(full_mode=settings.is_full_mode)
    )

    def _known_usernames() -> list[str]:
        """Sample handles available offline, to populate the demo hints."""
        connector = data_engine._connectors.get(Platform.TWITTER)
        return sorted(getattr(connector, "fixtures", {}).keys())

    @app.route("/", methods=["GET"])
    def index():
        return render_template_string(
            _PAGE,
            report=None,
            points=[],
            error=None,
            form={"username_a": "", "username_b": "", "post_limit": 100,
                  "bidirectional": True},
            known=_known_usernames(),
            mode=settings.analyzer_mode,
        )

    @app.route("/analyze", methods=["POST"])
    def analyze():
        form = {
            "username_a": request.form.get("username_a", "").strip(),
            "username_b": request.form.get("username_b", "").strip(),
            "post_limit": int(request.form.get("post_limit", 100) or 100),
            "bidirectional": request.form.get("bidirectional") == "on",
        }
        report = None
        points: list[dict] = []
        error = None
        if not form["username_a"] or not form["username_b"]:
            error = "Please provide both account handles."
        else:
            try:
                report_obj = shield.compare_via_engine(
                    data_engine,
                    Platform.TWITTER,
                    form["username_a"],
                    form["username_b"],
                    post_limit=form["post_limit"],
                    bidirectional=form["bidirectional"],
                )
                report = report_obj.to_dict()
                # Embed every directed message for the right-hand visualisation.
                points = _conversation_points(report_obj)
            except Exception as exc:  # surface engine/connector errors to the UI
                error = str(exc)
        return render_template_string(
            _PAGE,
            report=report,
            points=points,
            error=error,
            form=form,
            known=_known_usernames(),
            mode=settings.analyzer_mode,
        )

    return app


# --------------------------------------------------------------------------- #
# Inline template. Kept self-contained (CSS in <style>) for portability.
# --------------------------------------------------------------------------- #
_PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CyberShield — Abuse Comparison</title>
  <style>
    :root {
      --bg: #0f1320; --panel: #1a2032; --ink: #e8ecf5; --muted: #95a0bb;
      --accent: #4f8cff; --ok: #2fbf71; --warn: #f5a623;
      --bad: #e0533d; --line: #2a3247;
    }
    * { box-sizing: border-box; }
    body { margin:0; font-family: -apple-system, Segoe UI, Roboto, sans-serif;
           background: var(--bg); color: var(--ink); line-height: 1.5; }
    header { padding: 22px 28px; border-bottom: 1px solid var(--line);
             display:flex; align-items:center; gap:14px; }
    header h1 { font-size: 20px; margin:0; }
    header .shield { font-size: 26px; }
    header .mode { margin-left:auto; font-size:12px; color:var(--muted);
                   border:1px solid var(--line); padding:4px 10px; border-radius:20px; }
    main { max-width: 1080px; margin: 0 auto; padding: 26px; }
    .card { background: var(--panel); border:1px solid var(--line);
            border-radius: 14px; padding: 22px; margin-bottom: 22px; }
    label { display:block; font-size:13px; color:var(--muted); margin-bottom:6px; }
    input[type=text], input[type=number] {
      width:100%; padding:11px 12px; border-radius:9px; border:1px solid var(--line);
      background:#0c1019; color:var(--ink); font-size:15px; }
    .row { display:flex; gap:16px; flex-wrap:wrap; }
    .row > div { flex:1; min-width: 220px; }
    .controls { display:flex; align-items:center; gap:18px; margin-top:16px; flex-wrap:wrap; }
    .checkbox { display:flex; align-items:center; gap:8px; color:var(--muted); font-size:14px; }
    button { background: var(--accent); color:#fff; border:0; padding:12px 22px;
             border-radius:9px; font-size:15px; font-weight:600; cursor:pointer; }
    button:hover { filter:brightness(1.08); }
    .hint { font-size:12.5px; color:var(--muted); margin-top:10px; }
    .hint code { background:#0c1019; padding:2px 6px; border-radius:5px; }
    .error { background:#3a1c1c; border:1px solid #5e2b2b; color:#ffc9c0;
             padding:12px 14px; border-radius:9px; }
    .verdict { display:flex; align-items:center; gap:14px; margin-bottom:8px; }
    .badge { padding:6px 14px; border-radius:20px; font-weight:700; font-size:14px; }
    .b-abuse_detected { background: rgba(224,83,61,.18); color:#ff8a76; border:1px solid #5e2b2b;}
    .b-likely_abuse { background: rgba(245,166,35,.16); color:#ffc874; border:1px solid #5a4420;}
    .b-borderline { background: rgba(245,166,35,.10); color:#e6c98a; border:1px solid #4a3c20;}
    .b-no_abuse_detected { background: rgba(47,191,113,.15); color:#7fe0a8; border:1px solid #235c3e;}
    .dir { border:1px solid var(--line); border-radius:11px; padding:16px; margin-top:14px; }
    .dir h3 { margin:0 0 10px; font-size:15px; }
    .metrics { display:flex; gap:22px; flex-wrap:wrap; color:var(--muted); font-size:13px; }
    .metrics b { color:var(--ink); font-size:16px; display:block; }
    .msg { background:#0c1019; border-left:3px solid var(--bad); padding:10px 12px;
           border-radius:7px; margin-top:10px; }
    .msg .score { float:right; color:#ff8a76; font-weight:700; }
    .terms { margin-top:6px; }
    .term { display:inline-block; background:rgba(224,83,61,.15); color:#ff9c8c;
            font-size:12px; padding:2px 8px; border-radius:12px; margin:2px 4px 0 0; }
    .aggressor { color:#ffb38a; font-size:14px; margin-top:6px; }

    /* Two-region results layout: report on the left, embedding on the right. */
    .results-grid { display:flex; gap:22px; align-items:flex-start; flex-wrap:wrap; }
    .report-col { flex:1 1 380px; min-width:300px; }
    .embed-col { flex:0 0 340px; max-width:360px; position:sticky; top:16px;
                 border-left:1px solid var(--line); padding-left:20px; }
    @media (max-width: 820px) {
      .embed-col { flex-basis:100%; max-width:100%; border-left:0; padding-left:0;
                   border-top:1px solid var(--line); padding-top:16px; position:static; }
    }
    .embed-title { margin:0 0 4px; font-size:15px; }
    .embed-sub { margin:0 0 12px; font-size:12px; color:var(--muted); }
    .embed-svg { width:100%; aspect-ratio:1/1; display:block; border-radius:10px; }
    .embed-bg { fill:#0c1019; stroke:var(--line); stroke-width:0.4; }
    .embed-axis { stroke:#222a3d; stroke-width:0.4; stroke-dasharray:1.5 1.5; }
    .embed-svg circle, .embed-svg rect[rx] { transition:opacity .15s; cursor:pointer; }
    .embed-svg circle:hover, .embed-svg rect:hover { opacity:0.75; }
    .embed-legend { display:flex; align-items:center; gap:12px; flex-wrap:wrap;
                    margin-top:12px; font-size:12px; color:var(--muted); }
    .embed-legend .dot { display:inline-block; width:10px; height:10px;
                         border-radius:50%; margin-right:5px; vertical-align:middle; }
    .embed-legend .mk-circle { display:inline-block; width:10px; height:10px;
                         border-radius:50%; background:var(--muted); margin-right:5px;
                         vertical-align:middle; }
    .embed-legend .mk-rect { display:inline-block; width:10px; height:10px;
                         border-radius:2px; background:var(--muted); margin-right:5px;
                         vertical-align:middle; }
    .embed-legend .legend-sep { width:1px; height:14px; background:var(--line); }

    footer { text-align:center; color:var(--muted); font-size:12px; padding:30px; }
  </style>
</head>
<body>
  <header>
    <span class="shield">🛡️</span>
    <h1>CyberShield — Abuse Comparison</h1>
    <span class="mode">analyzer: {{ mode }}</span>
  </header>
  <main>
    <form class="card" method="post" action="/analyze">
      <p style="margin-top:0;color:var(--muted)">
        Compare two accounts on Twitter/X to check whether one is directing
        abuse at the other. The engine isolates messages each account aims at
        the other, scores them, and explains the verdict.
      </p>
      <div class="row">
        <div>
          <label>Account A (handle)</label>
          <input type="text" name="username_a" value="{{ form.username_a }}"
                 placeholder="e.g. abuser_joe">
        </div>
        <div>
          <label>Account B (handle)</label>
          <input type="text" name="username_b" value="{{ form.username_b }}"
                 placeholder="e.g. kind_amy">
        </div>
        <div style="max-width:160px">
          <label>Max posts / account</label>
          <input type="number" name="post_limit" value="{{ form.post_limit }}" min="1" max="1000">
        </div>
      </div>
      <div class="controls">
        <span class="checkbox">
          <input type="checkbox" name="bidirectional" {% if form.bidirectional %}checked{% endif %}>
          Analyze both directions (A→B and B→A)
        </span>
        <button type="submit">Run comparison</button>
      </div>
      {% if known %}
      <p class="hint">Sample accounts available offline:
        {% for u in known %}<code>{{ u }}</code> {% endfor %}</p>
      {% endif %}
    </form>

    {% if error %}
      <div class="card"><div class="error">⚠️ {{ error }}</div></div>
    {% endif %}

    {% if report %}
      <div class="card">
        <div class="results-grid">
          <!-- LEFT REGION: the abuse report -->
          <div class="report-col">
            <div class="verdict">
              <span class="badge b-{{ report.overall_verdict }}">
                {{ report.overall_verdict.replace('_',' ')|upper }}
              </span>
              <span style="color:var(--muted)">{{ report.account_a }} ↔ {{ report.account_b }}</span>
            </div>
            {% if report.aggressor %}
              <div class="aggressor">Likely aggressor: <b>{{ report.aggressor }}</b></div>
            {% endif %}

            {% for dir in [report.a_to_b, report.b_to_a] if dir %}
              <div class="dir">
                <h3>{{ dir.from }} → {{ dir.to }}
                    <span class="badge b-{{ dir.verdict }}" style="font-size:12px">
                      {{ dir.verdict.replace('_',' ') }}</span></h3>
                <div class="metrics">
                  <span><b>{{ dir.directed_message_count }}</b> directed messages</span>
                  <span><b>{{ dir.abusive_message_count }}</b> flagged</span>
                  <span><b>{{ '%.2f'|format(dir.mean_abuse_score) }}</b> mean score</span>
                  <span><b>{{ '%.2f'|format(dir.max_abuse_score) }}</b> peak score</span>
                </div>
                {% for m in dir.flagged_messages %}
                  <div class="msg">
                    <span class="score">{{ '%.2f'|format(m.abuse_score) }}</span>
                    {{ m.text }}
                    {% if m.matched_terms %}
                      <div class="terms">
                        {% for t in m.matched_terms %}
                          <span class="term">{{ t.term }}{% if t.match=='fuzzy' %} (~{{ t.token }}){% endif %}</span>
                        {% endfor %}
                      </div>
                    {% endif %}
                  </div>
                {% endfor %}
                {% if dir.abusive_message_count == 0 %}
                  <p class="hint">No abusive messages detected in this direction.</p>
                {% endif %}
              </div>
            {% endfor %}
          </div>

          <!-- RIGHT REGION: conversation embedding -->
          <aside class="embed-col">
            <h3 class="embed-title">Conversation embedding</h3>
            <p class="embed-sub">
              Each marker is one directed message, placed by textual similarity
              (2-D projection of message vectors). Nearby points are similar text.
            </p>
            {% if points %}
              <svg class="embed-svg" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet"
                   role="img" aria-label="2-D embedding of conversation messages">
                <rect x="0" y="0" width="100" height="100" class="embed-bg" rx="2"/>
                <line x1="50" y1="0" x2="50" y2="100" class="embed-axis"/>
                <line x1="0" y1="50" x2="100" y2="50" class="embed-axis"/>
                {% for p in points %}
                  {% if p.shape == 'circle' %}
                    <circle cx="{{ p.x }}" cy="{{ p.y }}" r="2.6"
                            fill="{{ p.fill }}" stroke="#0c1019" stroke-width="0.5">
                      <title>[{{ p.direction_label }}] abuse {{ p.abuse_score }} · {{ p.sentiment }}&#10;{{ p.text }}</title>
                    </circle>
                  {% else %}
                    <rect x="{{ p.x - 2.4 }}" y="{{ p.y - 2.4 }}" width="4.8" height="4.8" rx="0.8"
                          fill="{{ p.fill }}" stroke="#0c1019" stroke-width="0.5">
                      <title>[{{ p.direction_label }}] abuse {{ p.abuse_score }} · {{ p.sentiment }}&#10;{{ p.text }}</title>
                    </rect>
                  {% endif %}
                {% endfor %}
              </svg>
              <div class="embed-legend">
                <span><span class="dot" style="background:#2fbf71"></span>clean</span>
                <span><span class="dot" style="background:#f5a623"></span>borderline</span>
                <span><span class="dot" style="background:#e0533d"></span>abusive</span>
                <span class="legend-sep"></span>
                <span><span class="mk-circle"></span>A→B</span>
                <span><span class="mk-rect"></span>B→A</span>
              </div>
              <p class="hint">{{ points|length }} message(s) embedded. Hover a marker to read it.</p>
            {% else %}
              <p class="hint">No directed messages to embed.</p>
            {% endif %}
          </aside>
        </div>
      </div>
    {% endif %}
  </main>
  <footer>CyberShield · three-engine platform · abuse comparison view</footer>
</body>
</html>
"""
