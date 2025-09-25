from fastapi import APIRouter
from fastapi.responses import HTMLResponse
ui = APIRouter(prefix="/wb")

HTML = """
<!doctype html><meta charset='utf-8'><title>J58 Local</title>
<style>body{font:14px system-ui;margin:20px;max-width:1000px} input{width:90px} pre{white-space:pre-wrap}</style>
<h2>J58 – Minimal UI</h2>

<section>
  <h3>AI Train</h3>
  samples <input id=cnt type=number value=200>
  <button id=g>Generate</button>
  lambda <input id=lmbd type=number value=0.001 step=0.001>
  <button id=tr>Train</button>
  k <input id=kk type=number value=5> pool <input id=pool type=number value=200>
  <button id=sg>Suggest</button>
  <button id=bb>Build Best</button>
</section>

<section>
  <h3>Quick Links</h3>
  <p>Docs: <a href="/docs" target="_blank">/docs</a></p>
</section>

<h3>Out</h3><pre id=out></pre>
<script>
async function post(u,b){const r=await fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b||{})}); if(!r.ok) throw new Error(await r.text()); return r.json()}
function show(j){ out.textContent = JSON.stringify(j,null,2) }
g.onclick =async ()=>show(await post('/wb/ai/j58/generate',{count:+cnt.value}))
tr.onclick=async ()=>show(await post('/wb/ai/j58/train',{lmbd:+lmbd.value}))
sg.onclick =async ()=>show(await post('/wb/ai/j58/suggest',{k:+kk.value,random_pool:+pool.value}))
bb.onclick =async ()=>show(await post('/wb/ai/j58/build_best',{k:1,random_pool:+pool.value}))
</script>
"""
@ui.get("/j58/ui", response_class=HTMLResponse)
def j58_ui(): return HTML
