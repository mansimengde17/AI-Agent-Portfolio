"""HTML diff report generation."""

from __future__ import annotations

import html
import os

from .compare import Comparison, utc_stamp

STATUS_COLORS = {"pass": "#2e7d32", "warn": "#e6a700", "critical": "#c62828"}


def render_report(candidate: dict, comparison: Comparison,
                  history: list[float], out_dir: str = "reports") -> str:
    os.makedirs(out_dir, exist_ok=True)
    color = STATUS_COLORS[comparison.status]

    baseline_rate = ("n/a" if comparison.baseline_pass_rate is None
                     else f"{comparison.baseline_pass_rate:.1%}")
    delta = ("n/a" if comparison.delta is None
             else f"{comparison.delta:+.1%}")

    regression_rows = "".join(
        f"<tr><td>{html.escape(r['case_id'])}</td>"
        f"<td>{html.escape(r['difficulty'])}</td>"
        f"<td>{html.escape(r['expected'])}</td>"
        f"<td>{html.escape(r['old_output'])}<br>"
        f"<small>{html.escape(r['old_summary'])}</small></td>"
        f"<td class='bad'>{html.escape(r['new_output'])}<br>"
        f"<small>{html.escape(r['new_summary'])}</small></td></tr>"
        for r in comparison.regressions
    ) or "<tr><td colspan='5'>No regressed cases.</td></tr>"

    category_rows = "".join(
        f"<tr><td>{html.escape(cat)}</td><td>{d:+.1%}</td></tr>"
        for cat, d in comparison.category_deltas.items()
    ) or "<tr><td colspan='2'>No baseline for category deltas.</td></tr>"

    trend = " ".join(f"{r:.0%}" for r in reversed(history)) or "n/a"
    messages = "".join(f"<li>{html.escape(m)}</li>" for m in comparison.messages)

    page = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Eval diff report</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #222; }}
.badge {{ display: inline-block; padding: .3rem .8rem; border-radius: 4px;
         color: #fff; background: {color}; font-weight: 600; }}
table {{ border-collapse: collapse; margin: 1rem 0; width: 100%; }}
td, th {{ border: 1px solid #ccc; padding: .4rem .6rem; text-align: left;
          vertical-align: top; }}
th {{ background: #f2f2f2; }}
.bad {{ background: #fdecea; }}
small {{ color: #666; }}
</style></head><body>
<h1>Model Regression Detection: eval diff report</h1>
<p><span class="badge">{comparison.status.upper()}</span></p>
<h2>Run metadata</h2>
<table>
<tr><th>Prompt version</th><td>{html.escape(comparison.candidate_version)}</td></tr>
<tr><th>Baseline version</th><td>{html.escape(comparison.baseline_version or 'none')}</td></tr>
<tr><th>Model</th><td>{html.escape(candidate['model'])} via {html.escape(candidate['provider'])}</td></tr>
<tr><th>Generated</th><td>{utc_stamp()}</td></tr>
</table>
<h2>Scorecard</h2>
<table>
<tr><th>Baseline pass rate</th><th>Candidate pass rate</th><th>Delta</th></tr>
<tr><td>{baseline_rate}</td><td>{candidate['pass_rate']:.1%}</td><td>{delta}</td></tr>
</table>
<ul>{messages}</ul>
<h2>Regressed cases (old output vs new output)</h2>
<table>
<tr><th>Case</th><th>Difficulty</th><th>Expected</th><th>Previous run</th><th>This run</th></tr>
{regression_rows}
</table>
<h2>Per-category accuracy delta</h2>
<table><tr><th>Category</th><th>Delta</th></tr>{category_rows}</table>
<h2>Pass-rate trend (oldest to newest)</h2>
<p>{trend}</p>
</body></html>"""

    path = os.path.join(out_dir, "latest.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(page)
    return path
