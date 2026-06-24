"""Local web UI for the SAT ITR Requirement List generator.

    python app.py            # serves on http://localhost:5000
    PORT=8080 python app.py  # custom port

Paste / upload a client JSON spec, click Generate, and download the branded
.xlsx and the reconciliation memo.  Uses the same satrl package as the CLI.
"""

from __future__ import annotations

import io
import json
import os
import re

from flask import (Flask, Response, abort, render_template_string, request,
                   send_file)

from satrl.builder import build_requirement_xlsx
from satrl.loader import load_client
from satrl.memo import build_reconciliation_memo

app = Flask(__name__)

EXAMPLE_PATH = os.path.join(os.path.dirname(__file__), "examples", "nitin_kumar_jain.json")

# In-memory store of the most recent generation, keyed by a token, so the
# result page can offer downloads without re-running.  Single-process dev use.
_LAST = {}


def _slug(name: str) -> str:
    return re.sub(r"\s+", "_", name.strip()) or "Client"


def _fy_token(prev: str) -> str:
    m = re.match(r"\s*(\d{4})-(\d{2})", prev or "")
    return f"{m.group(1)}{m.group(2)}" if m else "FY"


PAGE = """
<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1">
<title>SAT ITR Requirement List Generator</title>
<style>
  :root{--charcoal:#404042;--orange:#EB8025;--lo:#FBE3CC;}
  *{box-sizing:border-box} body{margin:0;font-family:Calibri,Segoe UI,Arial,sans-serif;
    color:#222;background:#f4f4f4}
  header{background:var(--charcoal);color:#fff;padding:18px 24px}
  header h1{margin:0;font-size:20px;letter-spacing:.5px}
  header .sub{color:#F2C9A0;font-size:12.5px;margin-top:4px}
  .bar{height:5px;background:var(--orange)}
  main{max-width:1000px;margin:22px auto;padding:0 18px;display:grid;
    grid-template-columns:1fr;gap:18px}
  .card{background:#fff;border:1px solid #e3e3e3;border-radius:8px;padding:18px}
  h2{font-size:15px;margin:0 0 12px;color:var(--charcoal)}
  textarea{width:100%;height:340px;font-family:ui-monospace,Menlo,Consolas,monospace;
    font-size:12.5px;border:1px solid #ccc;border-radius:6px;padding:10px}
  .row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:12px}
  button,.btn{background:var(--orange);color:#fff;border:0;border-radius:6px;
    padding:10px 18px;font-size:14px;cursor:pointer;text-decoration:none;display:inline-block}
  button.secondary{background:#777}
  .pill{background:var(--lo);color:var(--charcoal);padding:8px 12px;border-radius:6px;
    font-weight:bold;font-size:13px}
  .err{background:#fdecea;border:1px solid #f5c2bd;color:#9b2c20;padding:10px 12px;
    border-radius:6px;white-space:pre-wrap;font-size:13px}
  pre{background:#fafafa;border:1px solid #eee;border-radius:6px;padding:12px;
    overflow:auto;font-size:12.5px;max-height:360px}
  input[type=file]{font-size:13px}
  .muted{color:#777;font-size:12px}
</style></head><body>
<header>
  <h1>SHREE ACCOUNTING &amp; TAXATION</h1>
  <div class=sub>ITR Requirement List Generator &nbsp;•&nbsp; paste a client JSON spec and generate the branded list + memo</div>
</header><div class=bar></div>
<main>
  <form class=card method=post action="/generate" enctype="multipart/form-data">
    <h2>Client JSON spec</h2>
    <textarea name=spec spellcheck=false>{{ spec }}</textarea>
    <div class=row>
      <button type=submit>Generate</button>
      <label class="btn secondary" style="cursor:pointer">Upload .json
        <input type=file name=specfile accept=".json,application/json" hidden
               onchange="this.form.submit()"></label>
      <a class="btn secondary" href="/">Reset to example</a>
      <span class=muted>Tip: edit the spec then click Generate.</span>
    </div>
  </form>

  {% if error %}<div class=card><h2>Error</h2><div class=err>{{ error }}</div></div>{% endif %}

  {% if result %}
  <div class=card>
    <h2>Result</h2>
    <div class=row>
      <span class=pill>Form: {{ result.form }}</span>
      <span class=pill>Due: {{ result.due }}</span>
      <a class=btn href="/download/{{ result.token }}/xlsx">Download .xlsx</a>
      <a class=btn href="/download/{{ result.token }}/memo">Download memo</a>
    </div>
    <h2 style="margin-top:18px">Reconciliation memo</h2>
    <pre>{{ result.memo }}</pre>
  </div>
  {% endif %}
</main></body></html>
"""


@app.get("/")
def index():
    with open(EXAMPLE_PATH, encoding="utf-8") as fh:
        return render_template_string(PAGE, spec=fh.read(), result=None, error=None)


@app.post("/generate")
def generate():
    upload = request.files.get("specfile")
    if upload and upload.filename:
        raw = upload.read().decode("utf-8")
    else:
        raw = request.form.get("spec", "")

    try:
        spec = json.loads(raw)
    except json.JSONDecodeError as exc:
        return render_template_string(PAGE, spec=raw, result=None,
                                      error=f"Invalid JSON: {exc}")
    try:
        client, bank_diag, inv_diag = load_client(spec)
        xbuf = io.BytesIO()
        decision = build_requirement_xlsx(client, xbuf)
        xbuf.seek(0)
        memo = build_reconciliation_memo(client, bank_diag, inv_diag, decision)
    except Exception as exc:  # surface model/normalisation errors to the user
        return render_template_string(PAGE, spec=raw, result=None,
                                      error=f"{type(exc).__name__}: {exc}")

    base = f"Requirement_{_slug(client.particulars.name)}_FY_{_fy_token(client.particulars.previous_year)}"
    token = _slug(client.particulars.name).lower()
    _LAST[token] = {"xlsx": xbuf.getvalue(), "memo": memo, "base": base}

    return render_template_string(
        PAGE, spec=raw, error=None,
        result={"form": decision.form, "due": decision.due_date,
                "memo": memo, "token": token})


@app.get("/download/<token>/<kind>")
def download(token, kind):
    item = _LAST.get(token)
    if not item:
        abort(404)
    if kind == "xlsx":
        return send_file(io.BytesIO(item["xlsx"]), as_attachment=True,
                         download_name=item["base"] + ".xlsx",
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    if kind == "memo":
        return Response(item["memo"], mimetype="text/plain",
                        headers={"Content-Disposition":
                                 f'attachment; filename="{item["base"]}_memo.txt"'})
    abort(404)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
