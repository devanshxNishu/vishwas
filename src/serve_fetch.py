"""
Live browser dashboard for the bulk GEFS fetch.

Companion to watch_fetch.py: same manifest, same clock discipline, pushed to a
browser over server-sent events instead of redrawn in a terminal.

    python src/serve_fetch.py                 # http://localhost:8777
    python src/serve_fetch.py --port 9000 --total 156

Standard library only. READ-ONLY -- it opens the manifest and nothing else, so
it cannot disturb a running fetch. Ctrl-C to stop.

WHY SSE AND NOT A META-REFRESH. Dates land about 80s apart, so a page that
reloads on a timer is stale most of the time and flickers when it isn't. The
server watches the manifest and pushes the moment it changes; between pushes
the page counts up the in-flight date locally, so there is always motion and it
is always truthful.

THE CLOCK, same trap as watch_fetch.py: 02_features.py stamps `finished` with
datetime.now() and no timezone, so the manifest carries MACHINE-LOCAL time. All
local-time arithmetic happens HERE, on the machine that wrote it, and only
elapsed seconds go to the browser -- so the page cannot be wrong about the
clock even if it is open on another device.
"""

import argparse, datetime, json, os, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "data", "raw", "manifest.jsonl")
NEW_YEARS = ("2015", "2016", "2017")
TOTAL = 156
WARMUP = 3      # first N dates pay connection setup; excluded from the rate
STALL_MIN = 8   # minutes without a new date before the page says so


def read_new():
    rows = []
    try:
        with open(MANIFEST) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try: rows.append(json.loads(line))
                    except json.JSONDecodeError: pass
    except FileNotFoundError:
        return []
    return [r for r in rows if str(r.get("init", "")).startswith(NEW_YEARS)]


def snapshot():
    new = read_new()
    n = len(new)
    d = {"n": n, "total": TOTAL, "left": TOTAL - n,
         "pct": (n / TOTAL * 100) if TOTAL else 0,
         "gb": sum(r["bytes"] for r in new) / 1e9,
         "rate": None, "spd": None, "eta_h": None, "eta": None,
         "since": None, "stall_min": STALL_MIN, "rows": []}
    if not n:
        return d
    try:
        fin = datetime.datetime.fromisoformat(new[-1]["finished"])
        d["since"] = max(0.0, (datetime.datetime.now() - fin).total_seconds())
    except Exception:
        pass
    w = (new[WARMUP:] if n > WARMUP else new)[-10:]
    if w:
        secs = sum(r["seconds"] for r in w) / len(w)
        d["rate"] = secs
        d["spd"] = sum(r["bytes"] for r in w) / sum(r["seconds"] for r in w) / 1e6
        rem = d["left"] * secs
        d["eta_h"] = rem / 3600
        d["eta"] = (datetime.datetime.now() +
                    datetime.timedelta(seconds=rem)).strftime("%a %H:%M")
    for r in reversed(new[-15:]):
        d["rows"].append({"init": str(r["init"]), "mb": r["bytes"] / 1e6,
                          "s": r["seconds"], "spd": r["bytes"] / 1e6 / r["seconds"],
                          "fin": str(r["finished"])[11:19]})
    return d


PAGE = """<!doctype html><html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>VISHWAS fetch</title><style>
*{box-sizing:border-box}
body{margin:0;background:#0e1116;color:#e9ecf0;
 font:15px/1.6 ui-sans-serif,-apple-system,"Segoe UI",Helvetica,Arial,sans-serif}
.w{max-width:760px;margin:0 auto;padding:40px 22px 60px}
h1{font-size:13px;letter-spacing:.14em;text-transform:uppercase;color:#78808b;
 font-weight:600;margin:0 0 4px}
.live{font-size:11px;color:#54c398;letter-spacing:.08em;text-transform:uppercase;
 margin-bottom:24px;display:flex;align-items:center;gap:7px}
.dot{width:7px;height:7px;border-radius:50%;background:#54c398;
 animation:p 1.8s ease-in-out infinite}
.dot.off{background:#78808b;animation:none}
@keyframes p{0%,100%{opacity:1}50%{opacity:.25}}
@media (prefers-reduced-motion:reduce){.dot{animation:none}}
.big{font-size:64px;font-weight:600;letter-spacing:-.03em;line-height:1;
 font-variant-numeric:tabular-nums}
.big span{font-size:26px;color:#78808b;font-weight:400;letter-spacing:0}
.bar{height:8px;background:#1b212a;border-radius:4px;margin:22px 0 8px;overflow:hidden}
.bar i{display:block;height:100%;background:#2a78d6;border-radius:4px;
 transition:width .6s cubic-bezier(.4,0,.2,1)}
.sub{font-size:13px;color:#78808b;margin-bottom:14px}
.now{background:#151a21;border:1px solid #232a33;border-radius:7px;
 padding:13px 16px;margin-bottom:22px;font-size:14px;display:flex;
 justify-content:space-between;align-items:baseline;gap:14px}
.now b{color:#78808b;font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;
 font-weight:600}
.now u{text-decoration:none;font-family:ui-monospace,Menlo,monospace;
 font-variant-numeric:tabular-nums;font-size:19px;font-weight:600}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));
 gap:10px;margin-bottom:30px}
.c{background:#151a21;border:1px solid #232a33;border-radius:7px;padding:13px 15px}
.c b{display:block;font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;
 color:#78808b;margin-bottom:7px;font-weight:600}
.c u{text-decoration:none;font-size:20px;font-weight:600;
 font-variant-numeric:tabular-nums}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;
 color:#78808b;font-weight:600;padding:0 10px 8px 0;border-bottom:1px solid #232a33}
td{padding:7px 10px 7px 0;border-bottom:1px solid #171d24}
.m{font-family:ui-monospace,Menlo,monospace;font-variant-numeric:tabular-nums}
.r{text-align:right}.dim{color:#78808b}
tr.slow td{color:#e08f5c}
tr.fresh{animation:in .8s ease-out}
@keyframes in{from{background:#16243a}to{background:transparent}}
@media (prefers-reduced-motion:reduce){tr.fresh{animation:none}}
.msg{padding:12px 15px;border-radius:7px;margin-bottom:22px;font-size:14px;display:none}
.msg.warn{background:#2a1c12;border:1px solid #7a4a28;color:#e08f5c;display:block}
.msg.ok{background:#12271f;border:1px solid #2c6a4f;color:#54c398;display:block}
.f{margin-top:26px;font-size:12px;color:#78808b}
</style></head><body><div class=w>
<h1>VISHWAS &middot; five-year fetch</h1>
<div class=live><span class=dot id=dot></span><span id=conn>connecting</span></div>
<div class=msg id=msg></div>
<div class=big><span id=n>&mdash;</span><span> / <span id=tot>156</span> dates</span></div>
<div class=bar><i id=bar style="width:0%"></i></div>
<div class=sub><span id=pct>0.0</span>% &middot; <span id=gb>0.0</span> GB fetched
 &middot; 2015&ndash;2017</div>
<div class=now><span><b>current date</b></span>
 <span><u id=cur>&mdash;</u> <span class=dim id=curof></span></span></div>
<div class=grid>
 <div class=c><b>per date</b><u id=rate>&mdash;</u></div>
 <div class=c><b>throughput</b><u id=spd>&mdash;</u></div>
 <div class=c><b>remaining</b><u id=left>&mdash;</u></div>
 <div class=c><b>eta</b><u id=eta>&mdash;</u></div>
</div>
<table><thead><tr><th>init</th><th class=r>size</th><th class=r>time</th>
<th class=r>rate</th><th>finished</th></tr></thead><tbody id=tb></tbody></table>
<div class=f>Rate is the mean of the last 10 dates, excluding the first 3.
Pushed live as the manifest is written; the current-date clock ticks locally
between writes. Read-only.</div>
</div><script>
var since=0, rate=null, seen={}, first=true, stallMin=8;
function fmt(s){s=Math.max(0,Math.round(s));var m=Math.floor(s/60);
 return m?m+"m "+String(s%60).padStart(2,"0")+"s":s+"s";}
function el(i){return document.getElementById(i);}
function tick(){
  since+=1;
  el("cur").textContent=fmt(since);
  el("curof").textContent=rate?("of ~"+Math.round(rate)+"s typical"):"";
  var m=el("msg");
  if(rate&&since>stallMin*60){
    m.className="msg warn";
    m.textContent="No new date for "+fmt(since)+". Dates normally take about "
      +Math.round(rate)+"s \\u2014 the fetch may have stopped, or the laptop slept.";
  }else if(m.className.indexOf("ok")<0){m.className="msg";}
}
setInterval(tick,1000);
function render(d){
  stallMin=d.stall_min;
  el("n").textContent=d.n; el("tot").textContent=d.total;
  el("pct").textContent=d.pct.toFixed(1); el("gb").textContent=d.gb.toFixed(1);
  el("bar").style.width=d.pct.toFixed(2)+"%";
  rate=d.rate; since=d.since==null?0:d.since;
  el("rate").textContent=d.rate?Math.round(d.rate)+" s":"\\u2014";
  el("spd").textContent=d.spd?d.spd.toFixed(2)+" MB/s":"\\u2014";
  el("left").textContent=d.eta_h?d.eta_h.toFixed(1)+" h":"\\u2014";
  el("eta").textContent=d.eta||"\\u2014";
  if(d.n>=d.total){var m=el("msg");m.className="msg ok";
    m.textContent="Fetch complete \\u2014 "+d.n+" dates, "+d.gb.toFixed(1)
      +" GB. Next: the schema assertion on the combined table.";
    el("cur").textContent="done";el("curof").textContent="";}
  var tb=el("tb"),h="";
  d.rows.forEach(function(r){
    var isNew=!first&&!seen[r.init]; seen[r.init]=1;
    h+="<tr class='"+(r.spd<2?"slow ":"")+(isNew?"fresh":"")+"'>"
      +"<td class=m>"+r.init+"</td><td class='m r'>"+r.mb.toFixed(0)+" MB</td>"
      +"<td class='m r'>"+r.s.toFixed(0)+" s</td>"
      +"<td class='m r'>"+r.spd.toFixed(2)+" MB/s</td>"
      +"<td class='m dim'>"+r.fin+"</td></tr>";
  });
  tb.innerHTML=h; first=false; tick();
}
var es=new EventSource("/events");
es.onopen=function(){el("dot").className="dot";el("conn").textContent="live";};
es.onmessage=function(e){render(JSON.parse(e.data));};
es.onerror=function(){el("dot").className="dot off";
  el("conn").textContent="reconnecting";};
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _head(self, ctype, length=None):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        if length is None:
            self.send_header("Connection", "keep-alive")
        else:
            self.send_header("Content-Length", str(length))
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/events"):
            return self.stream()
        body = PAGE.encode()
        self._head("text/html; charset=utf-8", len(body))
        self.wfile.write(body)

    def stream(self):
        self._head("text/event-stream")
        sig, beat = None, time.time()
        try:
            while True:
                try:
                    st = os.stat(MANIFEST)
                    now = (st.st_mtime, st.st_size)
                except OSError:
                    now = None
                if now != sig:
                    sig = now
                    self.wfile.write(
                        b"data: " + json.dumps(snapshot()).encode() + b"\n\n")
                    self.wfile.flush()
                    beat = time.time()
                elif time.time() - beat > 15:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    beat = time.time()
                time.sleep(1)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8777)
    p.add_argument("--total", type=int, default=TOTAL)
    a = p.parse_args()
    TOTAL = a.total
    print("VISHWAS fetch dashboard  ->  http://localhost:%d   (Ctrl-C to stop)" % a.port)
    ThreadingHTTPServer(("127.0.0.1", a.port), H).serve_forever()
