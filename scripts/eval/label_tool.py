"""로컬 라벨링 도구 — 브라우저 UI, 단축키 한 번에 한 건.

    python scripts/eval/label_tool.py evaluation/sample_v1.csv
    python scripts/eval/label_tool.py evaluation/sample_v1.csv --mode retest

설계 의도:

  * **한 건 5~10초.** 키 하나로 주라벨이 정해지고 자동으로 다음 건으로 넘어간다.
    마우스를 쓰지 않아도 끝까지 갈 수 있다.
  * **별점을 기본으로 가린다.** 판정 규칙 R2 는 "별점과 본문이 충돌하면 본문이
    이긴다" 이다. 별점이 먼저 보이면 사람은 거기에 끌려간다. `r` 로 열어볼 수 있다.
  * **층(stratum)을 보여주지 않는다.** "지금은 불만어휘 검출 구간" 을 알면
    라벨이 그쪽으로 쏠린다. 표본 설계가 라벨을 오염시키면 안 된다.
  * **키를 누를 때마다 디스크에 쓴다.** 중간에 닫아도 잃는 것이 없다.
    같은 명령을 다시 실행하면 이어서 한다.

의존성은 표준 라이브러리뿐이다. 서버가 죽어도 CSV 는 온전하다.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import sys
import tempfile
import threading
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.eval.taxonomy import (  # noqa: E402  pylint: disable=wrong-import-position
    EXCLUDE,
    LABELS,
    TAXONOMY_VERSION,
)

SESSION_LIMIT = 60  # 이 건수를 넘기면 쉬라고 경고한다. 집중력이 떨어지면 기준이 흔들린다.
RETEST_FRACTION = 0.10


class Store:
    """CSV 를 읽고, 라벨이 바뀔 때마다 원자적으로 다시 쓴다."""

    def __init__(self, path: str, retest: bool):
        self.path = path
        self.retest = retest
        self.lock = threading.Lock()
        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            self.fieldnames = list(reader.fieldnames or [])
            self.rows = list(reader)
        for required in ("sample_id", "review_text", "primary_label"):
            if required not in self.fieldnames:
                raise SystemExit(f"표본 CSV 에 '{required}' 컬럼이 없습니다: {path}")
        self.indices = self._retest_indices() if retest else list(range(len(self.rows)))

    def _retest_indices(self) -> list[int]:
        """재검사 대상 10%. 시드가 아니라 review_id 해시로 고른다 —
        같은 표본이면 언제 돌려도 같은 건이 뽑히고, 재현 가능하다."""
        picked = []
        for i, row in enumerate(self.rows):
            key = row.get("review_id") or row["sample_id"]
            digest = hashlib.sha256(f"retest|{key}".encode("utf-8")).hexdigest()
            if int(digest[:8], 16) / 0xFFFFFFFF < RETEST_FRACTION:
                picked.append(i)
        return picked

    def view(self) -> list[dict]:
        """브라우저로 보낼 형태. 재검사 모드에서는 기존 라벨을 가린다."""
        out = []
        for i in self.indices:
            row = self.rows[i]
            out.append({
                "idx": i,
                "sample_id": row["sample_id"],
                "text": row["review_text"],
                "rating": row.get("rating", ""),
                "menu": row.get("menu", ""),
                "primary": "" if self.retest else row.get("primary_label", ""),
                "alt": "" if self.retest else row.get("alt_label", ""),
                "notes": "" if self.retest else row.get("notes", ""),
            })
        return out

    def set_label(self, idx: int, primary: str, alt: str, notes: str) -> None:
        with self.lock:
            row = self.rows[idx]
            row["primary_label"] = primary
            row["alt_label"] = alt
            row["notes"] = notes
            row["labeled_at"] = (
                datetime.now(timezone.utc).isoformat() if primary else ""
            )
            self._flush()

    def _flush(self) -> None:
        directory = os.path.dirname(self.path) or "."
        fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writeheader()
                writer.writerows(self.rows)
            os.replace(tmp, self.path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    def progress(self) -> dict:
        done = sum(1 for i in self.indices if self.rows[i].get("primary_label"))
        return {"done": done, "total": len(self.indices)}


PAGE = r"""<!doctype html>
<meta charset="utf-8">
<title>라벨링 — __MODE__</title>
<style>
  :root{--bg:#14161a;--fg:#e8eaed;--dim:#8b939e;--line:#2a2f37;--hl:#4c9aff;--ok:#3fb950;--warn:#d29922}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--fg);
       font:15px/1.65 -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo",sans-serif;
       display:grid;grid-template-columns:1fr 340px;height:100vh;overflow:hidden}
  main{padding:28px 36px;display:flex;flex-direction:column;min-width:0;overflow:hidden}
  aside{border-left:1px solid var(--line);padding:22px 20px;overflow-y:auto;background:#101216}
  .bar{height:3px;background:var(--line);border-radius:2px;margin-bottom:22px;flex:none}
  .bar>i{display:block;height:100%;background:var(--ok);border-radius:2px;transition:width .15s}
  .meta{display:flex;gap:16px;align-items:center;color:var(--dim);font-size:13px;
        margin-bottom:18px;flex:none;flex-wrap:wrap}
  .meta b{color:var(--fg);font-weight:600}
  .warn{color:var(--warn)}
  .review{flex:1;overflow-y:auto;font-size:21px;line-height:1.75;white-space:pre-wrap;
          word-break:break-word;padding:22px 24px;background:#1a1d23;border-radius:10px;
          border:1px solid var(--line)}
  .review.empty{color:var(--dim);font-style:italic;font-size:17px}
  .chosen{margin-top:18px;flex:none;display:flex;gap:10px;align-items:center;min-height:38px;
          flex-wrap:wrap}
  .tag{padding:5px 13px;border-radius:999px;font-size:14px;font-weight:600}
  .tag.p{background:#1f3d5c;color:#9fcbff;border:1px solid #2e5c8a}
  .tag.a{background:#2b2a1a;color:#e0cf8a;border:1px solid #4a462a}
  .tag.x{background:#3d1f1f;color:#ffb3b3;border:1px solid #6a2e2e}
  .note{flex:none;margin-top:12px}
  .note input{width:100%;background:#1a1d23;border:1px solid var(--line);color:var(--fg);
              padding:9px 12px;border-radius:7px;font:inherit;font-size:14px}
  .note input:focus{outline:none;border-color:var(--hl)}
  h3{font-size:11px;letter-spacing:.09em;color:var(--dim);text-transform:uppercase;
     margin:0 0 10px;font-weight:600}
  aside section{margin-bottom:22px}
  .cat{display:flex;gap:10px;padding:5px 7px;border-radius:6px;cursor:pointer;align-items:baseline}
  .cat:hover{background:#1a1d23}
  .cat kbd{background:#242830;border:1px solid var(--line);border-bottom-width:2px;
           border-radius:4px;padding:1px 7px;font:600 12px ui-monospace,monospace;
           color:var(--hl);flex:none;min-width:22px;text-align:center}
  .cat .ko{font-size:14px;font-weight:600}
  .cat .key{font-size:11px;color:var(--dim);font-family:ui-monospace,monospace}
  .cat .desc{display:none;font-size:12px;color:var(--dim);line-height:1.5;
             margin:4px 0 8px 32px}
  .cat.open + .desc{display:block}
  .help{font-size:12.5px;color:var(--dim);line-height:1.9}
  .help kbd{background:#242830;border:1px solid var(--line);border-radius:3px;
            padding:0 5px;font:600 11px ui-monospace,monospace;color:var(--fg)}
  .done{position:fixed;inset:0;background:var(--bg);display:flex;align-items:center;
        justify-content:center;flex-direction:column;gap:14px;font-size:19px}
</style>
<body>
<main>
  <div class="bar"><i id="pbar"></i></div>
  <div class="meta">
    <span><b id="pos">-</b> / <span id="tot">-</span></span>
    <span id="sid" style="font-family:ui-monospace,monospace"></span>
    <span id="rating"></span>
    <span id="menu"></span>
    <span id="session"></span>
  </div>
  <div class="review" id="text"></div>
  <div class="chosen" id="chosen"></div>
  <div class="note"><input id="notes" placeholder="메모 (m 키) — R10 으로 other 를 골랐으면 왜 애매했는지 한 줄"></div>
</main>
<aside>
  <section>
    <h3>카테고리 — 숫자·문자 키</h3>
    <div id="cats"></div>
  </section>
  <section>
    <h3>조작</h3>
    <div class="help">
      <kbd>키</kbd> 주라벨 지정 → 자동으로 다음<br>
      <kbd>Shift</kbd>+키 대체라벨 (최대 1개)<br>
      <kbd>e</kbd> 제외 (본문 없음·판정 불가)<br>
      <kbd>←</kbd> <kbd>→</kbd> 이동 &nbsp; <kbd>Backspace</kbd> 라벨 지우기<br>
      <kbd>m</kbd> 메모 &nbsp; <kbd>Esc</kbd> 메모 닫기<br>
      <kbd>r</kbd> 별점 보기/숨기기<br>
      <kbd>d</kbd> 카테고리 설명 펼치기<br>
      <kbd>g</kbd> 라벨 없는 첫 건으로 점프
    </div>
  </section>
  <section>
    <h3>판정 규칙 요약</h3>
    <div class="help">
      <b>R1</b> 가장 강한 불만 하나. 비슷하면 먼저 언급된 것<br>
      <b>R2</b> 별점과 본문이 충돌하면 본문이 이긴다<br>
      <b>R3</b> 원인이 적혀 있으면 원인 쪽<br>
      <b>R4</b> 늦어서 식었다 → 주 <b>온도</b> / 대체 <b>배달지연</b><br>
      <b>R5</b> 새서 식었다 → 주 <b>포장</b> / 대체 <b>온도</b><br>
      <b>R6</b> 양 vs 가격은 주어로. 못 가르면 <b>양</b><br>
      <b>R7</b> "다음엔 ~해주세요" 는 불만<br>
      <b>R8</b> 요청 무시 — 주방이면 <b>매장응대</b>, 라이더면 <b>라이더</b><br>
      <b>R9</b> 리뷰이벤트 서비스 누락 → <b>누락</b><br>
      <b>R10</b> 20초 넘으면 <b>기타</b> + 메모, 넘어간다
    </div>
  </section>
</aside>
<script>
const LABELS = __LABELS__, EXCLUDE = "__EXCLUDE__";
let rows = [], cur = 0, showRating = false, sessionCount = 0;

const byHotkey = {};
for (const [k, v] of Object.entries(LABELS)) byHotkey[v.hotkey] = k;

function drawCats(){
  const el = document.getElementById('cats');
  el.innerHTML = Object.entries(LABELS).map(([k,v]) =>
    `<div class="cat" data-k="${k}"><kbd>${v.hotkey}</kbd>`
    + `<span><span class="ko">${v.ko}</span> <span class="key">${k}</span></span></div>`
    + `<div class="desc">${v.includes}<br><span style="color:#7a5c5c">제외: ${v.excludes}</span></div>`
  ).join('') + `<div class="cat" data-k="${EXCLUDE}"><kbd>e</kbd>`
    + `<span><span class="ko">제외</span> <span class="key">본문 없음·판정 불가</span></span></div>`
    + `<div class="desc">분류 대상이 아니므로 분모에서 뺀다.</div>`;
  el.querySelectorAll('.cat').forEach(c =>
    c.onclick = () => setPrimary(c.dataset.k));
}

function render(){
  if (!rows.length) return;
  const r = rows[cur];
  document.getElementById('pos').textContent = cur + 1;
  document.getElementById('tot').textContent = rows.length;
  document.getElementById('sid').textContent = '#' + r.sample_id;
  document.getElementById('rating').textContent =
    showRating ? '별점 ' + r.rating : '별점 숨김 (r)';
  document.getElementById('rating').className = showRating ? '' : 'warn';
  document.getElementById('menu').textContent = r.menu ? r.menu.slice(0, 60) : '';

  const t = document.getElementById('text');
  const body = (r.text || '').trim();
  t.textContent = body || '(본문 없음 — e 로 제외)';
  t.className = 'review' + (body ? '' : ' empty');
  t.scrollTop = 0;

  const name = k => k === EXCLUDE ? '제외' : (LABELS[k] ? LABELS[k].ko : k);
  let tags = '';
  if (r.primary) tags += `<span class="tag ${r.primary === EXCLUDE ? 'x' : 'p'}">`
    + `주 ${name(r.primary)}</span>`;
  if (r.alt) tags += `<span class="tag a">대체 ${name(r.alt)}</span>`;
  document.getElementById('chosen').innerHTML = tags
    || '<span style="color:#8b939e;font-size:13px">라벨 없음</span>';
  document.getElementById('notes').value = r.notes || '';

  const done = rows.filter(x => x.primary).length;
  document.getElementById('pbar').style.width = (done / rows.length * 100) + '%';
  const s = document.getElementById('session');
  s.textContent = sessionCount >= __SESSION_LIMIT__
    ? `이번 세션 ${sessionCount}건 — 쉬었다 하세요. 기준이 흔들립니다`
    : (sessionCount ? `이번 세션 ${sessionCount}건` : '');
  s.className = sessionCount >= __SESSION_LIMIT__ ? 'warn' : '';

  if (done === rows.length) finish();
}

function save(r){
  fetch('/api/label', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({idx:r.idx, primary:r.primary||'', alt:r.alt||'',
                          notes:r.notes||''})});
}

function setPrimary(k){
  const r = rows[cur];
  const wasEmpty = !r.primary;
  r.primary = k;
  if (r.alt === k) r.alt = '';
  save(r);
  if (wasEmpty) sessionCount++;
  render();
  setTimeout(() => { if (cur < rows.length - 1) { cur++; render(); } }, 60);
}

function setAlt(k){
  const r = rows[cur];
  r.alt = (r.alt === k || r.primary === k) ? '' : k;
  save(r); render();
}

function clearLabel(){
  const r = rows[cur];
  r.primary = ''; r.alt = '';
  save(r); render();
}

function jumpUnlabeled(){
  const i = rows.findIndex(x => !x.primary);
  if (i >= 0) { cur = i; render(); }
}

function finish(){
  const d = document.createElement('div');
  d.className = 'done';
  d.innerHTML = '<div style="font-size:42px">✓</div>'
    + `<div>${rows.length}건 라벨링 완료</div>`
    + '<div style="color:#8b939e;font-size:14px">CSV 에 저장됐습니다. '
    + '터미널에서 Ctrl+C 로 서버를 닫으세요.</div>';
  d.onclick = () => d.remove();
  document.body.appendChild(d);
}

document.addEventListener('keydown', e => {
  const notes = document.getElementById('notes');
  if (document.activeElement === notes){
    if (e.key === 'Escape' || e.key === 'Enter'){
      const r = rows[cur]; r.notes = notes.value; save(r); notes.blur();
    }
    return;
  }
  if (e.metaKey || e.ctrlKey || e.altKey) return;

  if (e.key === 'ArrowRight'){ if (cur < rows.length-1){cur++; render();} return; }
  if (e.key === 'ArrowLeft'){ if (cur > 0){cur--; render();} return; }
  if (e.key === 'Backspace'){ e.preventDefault(); clearLabel(); return; }
  if (e.key === 'm'){ e.preventDefault(); notes.focus(); return; }
  if (e.key === 'r'){ showRating = !showRating; render(); return; }
  if (e.key === 'g'){ jumpUnlabeled(); return; }
  if (e.key === 'd'){
    document.querySelectorAll('.cat').forEach(c => c.classList.toggle('open'));
    return;
  }
  const key = e.key.toLowerCase();
  if (key === 'e' && !e.shiftKey){ setPrimary(EXCLUDE); return; }
  const label = byHotkey[key];
  if (label){ e.shiftKey ? setAlt(label) : setPrimary(label); }
});

fetch('/api/rows').then(r => r.json()).then(d => {
  rows = d.rows; drawCats(); jumpUnlabeled(); render();
});
</script>
"""


def make_handler(store: Store, mode: str):
    class Handler(BaseHTTPRequestHandler):
        # do_GET / do_POST 는 BaseHTTPRequestHandler 가 강제하는 이름이다.
        # pylint: disable=invalid-name
        def log_message(self, *_args):
            pass  # 요청마다 터미널을 채우면 진행 로그가 안 보인다

        def _send(self, code, body, ctype):
            data = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/":
                page = (
                    PAGE.replace("__LABELS__", json.dumps(LABELS, ensure_ascii=False))
                    .replace("__EXCLUDE__", EXCLUDE)
                    .replace("__MODE__", mode)
                    .replace("__SESSION_LIMIT__", str(SESSION_LIMIT))
                )
                self._send(200, page, "text/html; charset=utf-8")
            elif self.path == "/api/rows":
                self._send(
                    200,
                    json.dumps({"rows": store.view()}, ensure_ascii=False),
                    "application/json; charset=utf-8",
                )
            else:
                self._send(404, "not found", "text/plain; charset=utf-8")

        def do_POST(self):
            if self.path != "/api/label":
                self._send(404, "not found", "text/plain; charset=utf-8")
                return
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
            store.set_label(
                int(payload["idx"]),
                payload.get("primary", ""),
                payload.get("alt", ""),
                payload.get("notes", ""),
            )
            p = store.progress()
            print(f"\r  진행 {p['done']}/{p['total']}", end="", flush=True)
            self._send(200, json.dumps(p), "application/json; charset=utf-8")

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="로컬 라벨링 도구")
    parser.add_argument("sample", help="표본 CSV (build_sample.py 산출물)")
    parser.add_argument("--mode", choices=("label", "retest"), default="label",
                        help="retest: 10%% 를 라벨 가린 채 재라벨링 (재검사 신뢰도용)")
    parser.add_argument("--port", type=int, default=8777)
    parser.add_argument("--no-open", action="store_true", help="브라우저를 열지 않는다")
    args = parser.parse_args()

    target = args.sample
    if args.mode == "retest":
        target = os.path.splitext(args.sample)[0] + ".retest.csv"
        if not os.path.exists(target):
            shutil.copyfile(args.sample, target)
            print(f"재검사 사본 생성: {target}")

    store = Store(target, retest=args.mode == "retest")
    progress = store.progress()

    print("=" * 66)
    print(f"  라벨링 도구 — 체계 {TAXONOMY_VERSION} · 모드 {args.mode}")
    print("=" * 66)
    print(f"  파일     {target}")
    print(f"  대상     {progress['total']}건 (이미 라벨됨 {progress['done']}건)")
    if args.mode == "retest":
        print(f"  재검사   표본의 {RETEST_FRACTION:.0%} 를 이전 라벨을 가린 채 다시 답니다")
        print("           최초 라벨링에서 3일 이상 지난 뒤에 하세요.")
    print(f"\n  → http://127.0.0.1:{args.port}")
    print("  Ctrl+C 로 종료. 키를 누를 때마다 저장되므로 언제 닫아도 됩니다.\n")

    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(store, args.mode))
    if not args.no_open:
        threading.Timer(0.6, lambda: webbrowser.open(f"http://127.0.0.1:{args.port}")).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        done = store.progress()
        print(f"\n\n  저장됨: {done['done']}/{done['total']} → {target}")
        if done["done"] < done["total"]:
            print("  같은 명령을 다시 실행하면 이어서 합니다.")


if __name__ == "__main__":
    main()
