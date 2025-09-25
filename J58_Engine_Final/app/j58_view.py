from fastapi import APIRouter
from fastapi.responses import HTMLResponse
api = APIRouter(prefix="/wb")
HTML = """<!doctype html><html><head><meta charset='utf-8'><title>J58 Viewer</title>
<style>html,body{margin:0;height:100%;background:#0b0e12;color:#e8eef5;font-family:ui-sans-serif}
#top{display:flex;gap:.5rem;align-items:center;padding:8px 12px;background:#111827;position:sticky;top:0}
#view{position:fixed;inset:48px 0 0 0}button,input{background:#111;color:#eee;border:1px solid #333;border-radius:8px;padding:6px 10px}
</style></head><body>
<div id="top"><button id="btnLatest">latest</button><input id="url" placeholder="rel path e.g. j58_runs/..../j58_assembly.glb" style="flex:1"/>
<button id="btnLoad">load</button><label><input id="chkWire" type="checkbox"> wireframe</label></div>
<canvas id="view"></canvas>
<script type="module">
import * as THREE from "https://unpkg.com/three@0.160.0/build/three.module.js";
import {OrbitControls} from "https://unpkg.com/three@0.160.0/examples/jsm/controls/OrbitControls.js";
import {GLTFLoader} from "https://unpkg.com/three@0.160.0/examples/jsm/loaders/GLTFLoader.js";
const canvas=document.querySelector("#view"); const r=new THREE.WebGLRenderer({canvas,antialias:true});
const s=new THREE.Scene(); s.background=new THREE.Color(0x0b0e12);
const c=new THREE.PerspectiveCamera(50,2,0.1,5000); c.position.set(220,180,220);
const o=new OrbitControls(c,r.domElement); o.enableDamping=true;
s.add(new THREE.HemisphereLight(0xffffff,0x202030,.9)); const d=new THREE.DirectionalLight(0xffffff,.8); d.position.set(250,200,300); s.add(d);
s.add(new THREE.GridHelper(800,40,0x2a2f36,0x1a1f26));
let cur=null, wire=false; function setW(m){ m.traverse(o=>{ if(o.isMesh){ o.material.wireframe=wire; o.material.metalness=.1; o.material.roughness=.8; o.material.color.setHex(0xb9c0ca);} }); }
async function loadRel(rel){ const loader=new GLTFLoader(); return new Promise((res,rej)=>loader.load("/wb/files/"+rel,g=>{ if(cur) s.remove(cur); cur=g.scene; setW(cur); s.add(cur); res(true);},undefined,rej)); }
async function latest(){ const r=await fetch("/wb/j58/latest"); if(!r.ok) throw 0; const j=await r.json(); u.value=j.rel_glb; return loadRel(j.rel_glb); }
const u=document.querySelector("#url"); document.querySelector("#btnLatest").onclick=()=>latest().catch(console.error);
document.querySelector("#btnLoad").onclick=()=>loadRel(u.value).catch(console.error);
document.querySelector("#chkWire").onchange=e=>{ wire=e.target.checked; if(cur) setW(cur); };
function resize(){ const w=innerWidth, h=innerHeight-48; r.setSize(w,h,false); c.aspect=w/h; c.updateProjectionMatrix(); } addEventListener("resize",resize); resize();
(function tick(){ o.update(); r.render(s,c); requestAnimationFrame(tick); })();
const q=new URLSearchParams(location.search); if(q.get("rel")){u.value=q.get("rel"); loadRel(u.value);} else { latest().catch(()=>{}); }
</script></body></html>"""
@api.get("/j58/view", response_class=HTMLResponse)
def j58_view(): return HTML
