import re

FILE = "static/index.html"
print("Reading " + FILE + "...")
with open(FILE, "r", encoding="utf-8") as f:
    html = f.read()

original = html

# ============================================================
# Replace entire CSS block with clean Claude-inspired design
# ============================================================
# Find <style> to </style> (first occurrence)
style_start = html.find("<style>")
style_end   = html.find("</style>", style_start) + len("</style>")
if style_start == -1 or style_end == -1:
    print("ERROR: Could not find <style> block")
    exit(1)

NEW_CSS = """<style>
/* ================================================================
   AUREX 3D - CLEAN UI v2
   Inspired by: minimal, calm, organized design
   Dark theme with gold + cyan accents
   ================================================================ */

/* ---- RESET ---- */
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%;overflow:hidden;font-family:'Inter',system-ui,sans-serif}

/* ---- TOKENS ---- */
:root{
  /* Backgrounds */
  --bg-0:#0a0e17;
  --bg-1:#0d1220;
  --bg-2:#111827;
  --bg-3:#1a2236;
  --bg-4:#1f2a40;
  --bg-5:#243049;

  /* Borders */
  --bd-1:rgba(255,255,255,0.06);
  --bd-2:rgba(255,255,255,0.10);
  --bd-3:rgba(255,255,255,0.14);

  /* Text */
  --tx-1:#f0f4ff;
  --tx-2:#a8b4cc;
  --tx-3:#6b7a99;
  --tx-4:#3d4d6a;

  /* Accent */
  --gold:#FFD700;
  --gold-dim:rgba(255,215,0,0.7);
  --gold-faint:rgba(255,215,0,0.12);
  --cyan:#00D4FF;
  --cyan-dim:rgba(0,212,255,0.6);
  --cyan-faint:rgba(0,212,255,0.08);
  --amber:#FFA500;
  --red:#FF4444;
  --green:#00CC88;

  /* Radius */
  --r-sm:4px;
  --r-md:8px;
  --r-lg:12px;

  /* Sidebar */
  --sidebar-w:220px;
  --right-w:320px;
  --topbar-h:48px;

  /* Nolan aliases for compatibility */
  --nolan-cyan:#00D4FF;
  --nolan-ice:#a8d8ff;
  --nolan-soft:rgba(0,212,255,0.15);
  --tara-amber:#FFA500;
  --tara-black:#0a0e17;
  --kuro-ochre:#c9a84c;
  --kube-white:#f0f4ff;
  --kube-red:#FF4444;
  --success:#00CC88;
  --bg-void:#0a0e17;
  --bg-deep:#0d1220;
  --bg-panel:#111827;
  --bg-card:#1a2236;
  --bg-input:#1f2a40;
  --bg-hover:#243049;
  --bg-active:#2a3655;
  --bg-select:#304070;
  --br-1:#1a2236;
  --br-2:rgba(255,255,255,0.06);
  --br-3:rgba(255,255,255,0.10);
  --br-focus:rgba(0,212,255,0.5);
  --text-1:#f0f4ff;
  --text-2:#a8b4cc;
  --text-3:#6b7a99;
  --text-4:#3d4d6a;
}

/* ---- BASE ---- */
body{background:var(--bg-0);color:var(--tx-1);cursor:none}
a{color:inherit;text-decoration:none}
button{cursor:pointer;border:none;background:none;font-family:inherit}
input,textarea,select{font-family:inherit;color:var(--tx-1)}
::selection{background:var(--nolan-soft);color:var(--cyan)}
::-webkit-scrollbar{width:4px;height:4px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--bd-2);border-radius:2px}
::-webkit-scrollbar-thumb:hover{background:var(--bd-3)}

/* ---- CUSTOM CURSOR ---- */
#cursor-dot,#cursor-ring{
  position:fixed;border-radius:50%;pointer-events:none;
  z-index:999999;transform:translate(-50%,-50%);
}
#cursor-dot{
  width:8px;height:8px;background:var(--gold);
  box-shadow:0 0 8px var(--gold),0 0 16px rgba(255,215,0,.5);
  transition:transform .08s ease,background .2s;
}
#cursor-ring{
  width:32px;height:32px;
  border:1px solid rgba(0,212,255,.5);
  box-shadow:0 0 8px rgba(0,212,255,.2);
  transition:width .15s,height .15s,border-color .15s;
}
body:has(button:hover) #cursor-dot,
body:has(a:hover) #cursor-dot{background:var(--cyan);}
body:has(button:hover) #cursor-ring,
body:has(a:hover) #cursor-ring{
  width:44px;height:44px;
  border-color:rgba(255,215,0,.7);
}
.cursor-trail{
  position:fixed;border-radius:50%;pointer-events:none;
  z-index:999998;transform:translate(-50%,-50%);
  background:rgba(0,212,255,.3);
}

/* ---- AURORA BG ---- */
#aurora-bg{
  position:fixed;inset:0;z-index:-1;pointer-events:none;overflow:hidden;
}
#aurora-bg::before{
  content:'';position:absolute;inset:-50%;
  background:
    radial-gradient(ellipse 80% 60% at 20% 30%,rgba(0,180,216,.05) 0%,transparent 60%),
    radial-gradient(ellipse 60% 80% at 80% 70%,rgba(255,215,0,.03) 0%,transparent 55%),
    radial-gradient(ellipse 70% 50% at 50% 50%,rgba(255,107,53,.02) 0%,transparent 60%);
  animation:auroraDrift 18s ease-in-out infinite alternate;
}
@keyframes auroraDrift{
  from{transform:translate(0,0) scale(1)}
  to{transform:translate(1.5%,1%) scale(1.04)}
}

/* ---- LOADING SCREEN ---- */
#loading-screen{
  position:fixed;inset:0;z-index:99999;
  background:var(--bg-0);
  display:flex;flex-direction:column;
  align-items:center;justify-content:center;gap:24px;
  transition:opacity .5s,visibility .5s;
}
#loading-screen.gone{opacity:0;visibility:hidden;pointer-events:none}
.ls-logo{
  font-family:'Orbitron',sans-serif;font-size:32px;font-weight:900;
  letter-spacing:8px;
  background:linear-gradient(135deg,var(--gold),#fff,var(--amber));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
  filter:drop-shadow(0 0 12px rgba(255,215,0,.4));
}
.ls-bar{
  width:160px;height:2px;background:var(--bd-1);border-radius:1px;overflow:hidden;
}
.ls-bar-fill{
  height:100%;width:0%;background:linear-gradient(90deg,var(--cyan),var(--gold));
  border-radius:1px;animation:lsLoad 1.8s ease forwards;
}
@keyframes lsLoad{to{width:100%}}
.ls-sub{
  font-family:'JetBrains Mono',monospace;font-size:10px;
  letter-spacing:3px;color:var(--tx-3);text-transform:uppercase;
}

/* ---- LOGIN OVERLAY ---- */
#login-overlay{
  position:fixed;inset:0;z-index:99998;
  display:flex;align-items:center;justify-content:center;
  background:rgba(10,14,23,0.92);
  backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);
}
#login-overlay.hidden{display:none}
#login-overlay canvas{position:absolute;inset:0;pointer-events:none}
#login-overlay canvas#ol-stars{z-index:0}
#login-overlay canvas#ol-grid{z-index:1}
#login-card{
  position:relative;z-index:2;width:380px;
  background:rgba(13,18,32,0.95);
  border:1px solid var(--bd-2);
  border-top:2px solid var(--gold);
  padding:40px 32px 32px;
  animation:cardIn .5s cubic-bezier(.16,1,.3,1);
}
@keyframes cardIn{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:none}}
#login-card::before{
  content:'';position:absolute;top:0;left:-100%;width:50%;height:2px;
  background:linear-gradient(90deg,transparent,var(--gold),transparent);
  animation:shimmer 2.5s ease-in-out infinite;
}
@keyframes shimmer{0%{left:-100%}100%{left:200%}}
.lc-corner{position:absolute;width:10px;height:10px}
.lc-tl{top:-1px;left:-1px;border-top:2px solid var(--cyan);border-left:2px solid var(--cyan)}
.lc-tr{top:-1px;right:-1px;border-top:2px solid var(--cyan);border-right:2px solid var(--cyan)}
.lc-bl{bottom:-1px;left:-1px;border-bottom:2px solid var(--cyan);border-left:2px solid var(--cyan)}
.lc-br{bottom:-1px;right:-1px;border-bottom:2px solid var(--cyan);border-right:2px solid var(--cyan)}
.lc-logo{
  font-family:'Orbitron',sans-serif;font-size:32px;font-weight:900;
  letter-spacing:6px;text-align:center;
  background:linear-gradient(135deg,var(--gold),#fff,var(--amber));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
  filter:drop-shadow(0 0 10px rgba(255,215,0,.3));margin-bottom:4px;
}
.lc-sub{
  text-align:center;font-family:'JetBrains Mono',monospace;
  font-size:10px;letter-spacing:5px;color:var(--cyan-dim);
  text-transform:uppercase;margin-bottom:20px;
}
.lc-divider{
  height:1px;background:linear-gradient(90deg,transparent,var(--gold),transparent);
  margin:0 0 20px;position:relative;
}
.lc-divider::before{
  content:'◆';position:absolute;left:50%;top:50%;
  transform:translate(-50%,-50%);color:var(--gold);font-size:7px;
  background:rgba(13,18,32,0.95);padding:0 8px;
}
.lc-btn{
  width:100%;padding:12px 16px;border-radius:var(--r-sm);
  font-family:'Inter',sans-serif;font-size:13px;font-weight:500;
  letter-spacing:1px;cursor:pointer;
  display:flex;align-items:center;justify-content:center;gap:8px;
  transition:all .15s;text-decoration:none;border:none;
  position:relative;overflow:hidden;
}
#lc-google{
  background:rgba(255,255,255,.05);
  border:1px solid rgba(255,255,255,.12);
  color:var(--tx-1);margin-bottom:10px;
}
#lc-google:hover{background:rgba(255,255,255,.09);border-color:rgba(255,255,255,.2)}
#lc-guest{
  background:linear-gradient(135deg,var(--amber),var(--gold));
  color:#0a0e17;font-weight:600;
}
#lc-guest:hover{box-shadow:0 4px 20px rgba(255,215,0,.35);transform:translateY(-1px)}
.lc-sep{
  display:flex;align-items:center;gap:10px;margin:12px 0;
  font-family:'JetBrains Mono',monospace;font-size:9px;
  color:rgba(255,255,255,.2);letter-spacing:2px;
}
.lc-sep::before,.lc-sep::after{content:'';flex:1;height:1px;background:rgba(255,255,255,.07)}
#lc-status{
  margin-top:18px;text-align:center;
  font-family:'JetBrains Mono',monospace;font-size:9px;
  color:var(--tx-3);letter-spacing:2px;
  display:flex;align-items:center;justify-content:center;gap:6px;
}
#lc-status-dot{
  width:5px;height:5px;border-radius:50%;
  background:var(--green);box-shadow:0 0 6px var(--green);
  animation:statusPulse 2s infinite;
}
@keyframes statusPulse{0%,100%{opacity:1}50%{opacity:.3}}
.ol-sig{
  position:absolute;bottom:16px;right:20px;z-index:3;
  font-family:'JetBrains Mono',monospace;font-size:10px;
  color:rgba(255,215,0,.25);letter-spacing:2px;
  transition:color .3s;
}
.ol-sig:hover{color:rgba(255,215,0,.7)}

/* ---- NAVBAR (left side) ---- */
#nav{
  position:fixed;top:0;left:0;bottom:0;
  width:48px;background:var(--bg-1);
  border-right:1px solid var(--bd-1);
  display:flex;flex-direction:column;
  align-items:center;padding:12px 0;gap:2px;
  z-index:100;
}
.nav-logo{
  font-family:'Orbitron',sans-serif;font-size:11px;font-weight:800;
  color:var(--gold);letter-spacing:1px;
  width:36px;height:36px;
  background:linear-gradient(135deg,var(--amber),var(--gold));
  border-radius:var(--r-sm);
  display:flex;align-items:center;justify-content:center;
  margin-bottom:12px;color:#0a0e17;
  box-shadow:0 0 12px rgba(255,215,0,.2);
}
.nav-item{
  width:36px;height:36px;border-radius:var(--r-sm);
  display:flex;align-items:center;justify-content:center;
  color:var(--tx-3);transition:all .15s;cursor:pointer;
  position:relative;
}
.nav-item:hover{background:var(--bg-3);color:var(--tx-1)}
.nav-item.active{background:var(--cyan-faint);color:var(--cyan)}
.nav-item svg{width:16px;height:16px;stroke:currentColor;fill:none;stroke-width:1.5}
.nav-tip{
  position:absolute;left:calc(100% + 8px);
  background:var(--bg-3);border:1px solid var(--bd-2);
  color:var(--tx-1);font-size:11px;padding:4px 8px;
  border-radius:var(--r-sm);white-space:nowrap;
  opacity:0;pointer-events:none;transition:opacity .15s;z-index:200;
}
.nav-item:hover .nav-tip{opacity:1}
.nav-ver{
  margin-top:auto;font-family:'JetBrains Mono',monospace;
  font-size:8px;color:var(--tx-4);letter-spacing:1px;
}
.nav-icon-grid{display:grid;grid-template-columns:1fr 1fr;gap:2px}
.nav-icon-grid span{width:5px;height:5px;background:currentColor;border-radius:.5px;display:block}
.nav-icon-wrench,.nav-icon-gear{
  width:16px;height:16px;border-radius:2px;
  border:1.5px solid currentColor;position:relative;
}
.nav-icon-q{font-size:14px;font-weight:600;color:currentColor}
/* Nav icons */
.ni-studio::before{content:'⬡';font-size:14px}
.ni-gallery::before{content:'⊞';font-size:14px}
.ni-workshop::before{content:'⚙';font-size:14px}
.ni-settings::before{content:'◈';font-size:14px}
.ni-help::before{content:'?';font-size:13px;font-weight:600}

/* ---- TOPBAR ---- */
#topbar{
  position:fixed;top:0;left:48px;right:0;height:var(--topbar-h);
  background:var(--bg-1);border-bottom:1px solid var(--bd-1);
  display:flex;align-items:center;padding:0 16px;gap:12px;
  z-index:99;
}
#page-title{
  font-family:'Orbitron',sans-serif;font-size:11px;font-weight:700;
  letter-spacing:3px;color:var(--tx-2);text-transform:uppercase;flex:1;
}
.topbar-right{display:flex;align-items:center;gap:10px}
.status-badge{
  display:flex;align-items:center;gap:5px;
  font-family:'JetBrains Mono',monospace;font-size:10px;
  letter-spacing:1px;padding:3px 8px;border-radius:20px;
  border:1px solid var(--bd-2);color:var(--tx-3);
  background:var(--bg-2);
}
.status-badge.generating{border-color:rgba(255,165,0,.4);color:var(--amber)}
.status-badge.error{border-color:rgba(255,68,68,.4);color:var(--red)}
.s-dot{width:5px;height:5px;border-radius:50%;background:currentColor;animation:statusPulse 2s infinite}
.model-counter{
  font-family:'JetBrains Mono',monospace;font-size:10px;
  color:var(--tx-3);letter-spacing:1px;
}
.model-counter em{color:var(--cyan-dim);font-style:normal;font-weight:500}
#install-btn{
  font-size:10px;padding:3px 8px;border-radius:3px;
  border:1px solid var(--bd-2);color:var(--tx-3);
  background:transparent;letter-spacing:1px;
  display:none;
}
#install-btn.shown{display:block}
.online-dot{
  width:7px;height:7px;border-radius:50%;
  background:var(--tx-4);transition:background .3s;
}
.online-dot.live{background:var(--green);box-shadow:0 0 6px var(--green)}
#user-avatar-wrap{
  display:none;align-items:center;gap:6px;cursor:pointer;
  padding:3px 8px 3px 4px;border-radius:20px;
  border:1px solid rgba(255,215,0,.15);
  background:rgba(255,215,0,.04);
  transition:all .15s;
}
#user-avatar-wrap:hover{border-color:rgba(255,215,0,.3);background:rgba(255,215,0,.08)}
#user-avatar{
  width:22px;height:22px;border-radius:50%;
  border:1px solid rgba(255,215,0,.4);object-fit:cover;
}
#user-name{
  font-size:11px;font-family:'Inter',sans-serif;font-weight:500;
  color:rgba(255,215,0,.8);max-width:100px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
}
#user-email{
  font-size:8px;color:var(--tx-3);
  max-width:100px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  display:block;
}

/* ---- CONTENT + PAGES ---- */
#content{
  position:fixed;top:var(--topbar-h);left:48px;right:0;bottom:0;
  display:flex;overflow:hidden;
}
.page{display:none;width:100%;height:100%}
.page.active{display:flex}

/* ---- STUDIO PAGE ---- */
#page-studio{display:flex}
#studio-left{
  width:var(--sidebar-w);flex-shrink:0;
  background:var(--bg-1);border-right:1px solid var(--bd-1);
  display:flex;flex-direction:column;overflow:hidden;
}
#studio-left-scroll{flex:1;overflow-y:auto;padding:12px 0}
.sec-head{
  display:flex;align-items:center;gap:6px;
  padding:6px 12px;
  font-family:'JetBrains Mono',monospace;font-size:9px;
  font-weight:500;letter-spacing:2px;text-transform:uppercase;
  color:var(--tx-3);
}
.sec-head.clickable{cursor:pointer;transition:color .15s;user-select:none}
.sec-head.clickable:hover{color:var(--tx-2)}
.sec-dot{
  width:5px;height:5px;border-radius:50%;flex-shrink:0;
}
.sec-dot.cyan{background:var(--cyan)}
.sec-dot.ochre{background:var(--kuro-ochre)}
.sec-arrow{
  margin-left:auto;font-size:8px;
  transition:transform .2s;color:inherit;
}
.sec-arrow.closed{transform:rotate(-90deg)}
.left-stats{padding:2px 12px 8px}
.stat-row{
  display:flex;align-items:center;justify-content:space-between;
  padding:4px 0;border-bottom:1px solid var(--bd-1);
}
.stat-row:last-child{border-bottom:none}
.stat-lbl{
  font-family:'JetBrains Mono',monospace;font-size:9px;
  letter-spacing:1px;color:var(--tx-4);text-transform:uppercase;
}
.stat-val{
  font-family:'JetBrains Mono',monospace;font-size:10px;
  font-weight:500;color:var(--tx-2);
}
.stat-val.amber{color:var(--amber)}
.stat-val.ochre{color:var(--kuro-ochre)}

/* ---- FOLDER LIST ---- */
.folder-sec{padding:4px 8px 8px}
.folder-list{display:flex;flex-direction:column;gap:1px}
.folder-row{
  display:flex;align-items:center;gap:6px;
  padding:6px 8px;border-radius:var(--r-sm);cursor:pointer;
  transition:all .12s;user-select:none;
}
.folder-row:hover{background:var(--bg-3);color:var(--tx-1)}
.folder-row.active{
  background:rgba(201,168,76,.1);
  border:1px solid rgba(201,168,76,.2);
}
.folder-icon-sh{
  font-size:12px;color:var(--tx-3);transition:color .12s;flex-shrink:0;
}
.folder-row.active .folder-icon-sh{color:var(--kuro-ochre)}
.folder-name-txt{
  font-size:12px;color:var(--tx-2);flex:1;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  transition:color .12s;
}
.folder-row.active .folder-name-txt{color:var(--kuro-ochre)}
.folder-count{
  font-family:'JetBrains Mono',monospace;font-size:9px;
  color:var(--tx-4);background:var(--bg-3);
  padding:1px 5px;border-radius:8px;min-width:18px;text-align:center;
}
.folder-row.active .folder-count{background:rgba(201,168,76,.15);color:var(--kuro-ochre)}
.folder-del-btn{
  font-size:12px;color:var(--tx-4);transition:color .12s;
  background:none;border:none;padding:0 2px;cursor:pointer;
  opacity:0;
}
.folder-row:hover .folder-del-btn{opacity:1}
.folder-del-btn:hover{color:var(--red)}
.folder-add-row{
  display:flex;gap:6px;padding:6px 8px 0;
}
.folder-add-inp{
  flex:1;background:var(--bg-2);border:1px solid var(--bd-2);
  border-radius:var(--r-sm);padding:5px 8px;
  font-size:11px;color:var(--tx-1);outline:none;
  transition:border-color .15s;
}
.folder-add-inp:focus{border-color:var(--cyan)}
.folder-add-inp::placeholder{color:var(--tx-4)}
.folder-add-btn{
  width:26px;height:26px;border-radius:var(--r-sm);
  background:var(--bg-3);border:1px solid var(--bd-2);
  color:var(--tx-2);font-size:16px;transition:all .15s;cursor:pointer;
  display:flex;align-items:center;justify-content:center;
}
.folder-add-btn:hover{background:var(--bg-4);color:var(--tx-1);border-color:var(--bd-3)}
.options-sec{padding:8px 12px 12px}
.toggle-row{
  display:flex;align-items:center;justify-content:space-between;
  padding:6px 0;
}
.toggle-lbl{font-size:11px;color:var(--tx-2)}
.toggle-sw{position:relative;cursor:pointer}
.toggle-sw input{display:none}
.toggle-track{
  width:30px;height:16px;border-radius:8px;
  background:var(--bg-4);border:1px solid var(--bd-2);
  transition:all .2s;
}
.toggle-thumb{
  position:absolute;top:2px;left:2px;
  width:12px;height:12px;border-radius:50%;
  background:var(--tx-3);transition:all .2s;
}
.toggle-sw input:checked + .toggle-track{
  background:rgba(0,212,255,.2);border-color:rgba(0,212,255,.4);
}
.toggle-sw input:checked + .toggle-track + .toggle-thumb{
  left:16px;background:var(--cyan);
}

/* ---- CENTER VIEWPORT ---- */
#studio-center{
  flex:1;position:relative;overflow:hidden;background:var(--bg-0);
}
#three-canvas{display:block;width:100%;height:100%}
.vp-vignette{
  position:absolute;inset:0;pointer-events:none;
  background:radial-gradient(ellipse 85% 85% at 50% 50%,transparent 60%,rgba(10,14,23,.4) 100%);
}
.vp-corner{
  position:absolute;width:20px;height:20px;pointer-events:none;
}
.vp-corner.tl{top:12px;left:12px;border-top:1px solid rgba(0,212,255,.25);border-left:1px solid rgba(0,212,255,.25)}
.vp-corner.tr{top:12px;right:12px;border-top:1px solid rgba(0,212,255,.25);border-right:1px solid rgba(0,212,255,.25)}
.vp-corner.bl{bottom:12px;left:12px;border-bottom:1px solid rgba(0,212,255,.25);border-left:1px solid rgba(0,212,255,.25)}
.vp-corner.br{bottom:12px;right:12px;border-bottom:1px solid rgba(0,212,255,.25);border-right:1px solid rgba(0,212,255,.25)}
#empty-state{
  position:absolute;inset:0;display:flex;flex-direction:column;
  align-items:center;justify-content:center;gap:12px;
  pointer-events:none;
}
.es-cube-wrap{position:relative;margin-bottom:8px}
.es-cube{
  width:40px;height:40px;border:1px solid rgba(0,212,255,.2);
  border-radius:4px;animation:esCubeSpin 8s linear infinite;
}
.es-cube-glow{
  position:absolute;inset:-8px;border-radius:12px;
  background:radial-gradient(circle,rgba(0,212,255,.05),transparent 70%);
  animation:esCubeSpin 8s linear infinite reverse;
}
@keyframes esCubeSpin{to{transform:rotate(360deg)}}
.es-title{
  font-family:'Orbitron',sans-serif;font-size:16px;font-weight:700;
  letter-spacing:4px;color:var(--tx-2);text-transform:uppercase;
}
.es-sub{font-size:12px;color:var(--tx-4);letter-spacing:1px}
.es-chips{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-top:4px;pointer-events:all}
.es-chip{
  padding:5px 12px;border-radius:20px;
  border:1px solid var(--bd-2);background:var(--bg-2);
  font-size:11px;color:var(--tx-3);cursor:pointer;
  transition:all .15s;
}
.es-chip:hover{border-color:var(--bd-3);color:var(--tx-1);background:var(--bg-3)}
#model-bar{
  position:absolute;bottom:52px;left:0;right:0;
  padding:6px 12px;display:none;
  background:rgba(10,14,23,.8);backdrop-filter:blur(8px);
  border-top:1px solid var(--bd-1);
  display:flex;align-items:center;gap:8px;
}
.mbar-prompt{
  font-size:11px;color:var(--tx-2);flex:1;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
}
.svc-badge{
  font-family:'JetBrains Mono',monospace;font-size:9px;
  padding:2px 7px;border-radius:3px;letter-spacing:1px;
  background:var(--bg-3);border:1px solid var(--bd-2);color:var(--tx-3);
}
.svc-badge.gemini{background:rgba(0,212,255,.08);border-color:rgba(0,212,255,.2);color:var(--cyan-dim)}
.svc-badge.blender{background:rgba(255,165,0,.08);border-color:rgba(255,165,0,.2);color:var(--amber)}
.mbar-size{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--tx-4)}
#model-quality{display:flex;gap:2px}
.q-star{font-size:10px;color:var(--tx-4)}.q-star.on{color:var(--gold)}
#vp-overlay{
  position:absolute;inset:0;
  background:rgba(10,14,23,.6);backdrop-filter:blur(4px);
  display:none;flex-direction:column;align-items:center;justify-content:center;gap:16px;
}
#vp-overlay.shown{display:flex}
.vp-spinner-wrap{position:relative;width:48px;height:48px}
.vp-ring-outer{
  position:absolute;inset:0;border-radius:50%;
  border:2px solid var(--bd-2);border-top-color:var(--cyan);
  animation:spin 1s linear infinite;
}
.vp-ring-inner{
  position:absolute;inset:8px;border-radius:50%;
  border:2px solid transparent;border-bottom-color:var(--gold);
  animation:spin .7s linear infinite reverse;
}
@keyframes spin{to{transform:rotate(360deg)}}
.vp-step-txt{
  font-family:'JetBrains Mono',monospace;font-size:11px;
  letter-spacing:2px;color:var(--tx-2);
}
#ctrl-bar{
  position:absolute;bottom:0;left:0;right:0;
  padding:8px 12px;display:flex;align-items:center;gap:6px;
  background:rgba(13,18,32,.9);backdrop-filter:blur(8px);
  border-top:1px solid var(--bd-1);
}
.ctrl-btn{
  padding:5px 10px;border-radius:var(--r-sm);
  font-family:'JetBrains Mono',monospace;font-size:10px;
  letter-spacing:1px;text-transform:uppercase;
  border:1px solid var(--bd-2);background:var(--bg-2);color:var(--tx-3);
  cursor:pointer;transition:all .12s;
}
.ctrl-btn:hover{background:var(--bg-3);border-color:var(--bd-3);color:var(--tx-1)}
.ctrl-btn.active{background:var(--cyan-faint);border-color:rgba(0,212,255,.3);color:var(--cyan)}
.ctrl-btn.wire.active{background:rgba(255,165,0,.08);border-color:rgba(255,165,0,.25);color:var(--amber)}
.save-btn{border-color:rgba(255,215,0,.25);color:var(--gold-dim)}
.save-btn:hover{background:rgba(255,215,0,.08);border-color:rgba(255,215,0,.4);color:var(--gold)}
.ctrl-sep{flex:1}

/* ---- RIGHT PANEL ---- */
#studio-right{
  width:var(--right-w);flex-shrink:0;
  background:var(--bg-1);border-left:1px solid var(--bd-1);
  display:flex;flex-direction:column;overflow:hidden;
}
#sheet-handle{
  width:32px;height:3px;background:var(--bd-2);
  border-radius:2px;margin:6px auto;display:none;
}
.r-tabbar{
  display:flex;border-bottom:1px solid var(--bd-1);
  padding:0 4px;flex-shrink:0;
}
.r-tab{
  flex:1;padding:10px 4px;
  font-family:'JetBrains Mono',monospace;font-size:9px;
  letter-spacing:1px;text-transform:uppercase;
  color:var(--tx-3);border-bottom:2px solid transparent;
  transition:all .15s;cursor:pointer;background:none;border:none;
  border-bottom:2px solid transparent;
}
.r-tab:hover{color:var(--tx-2)}
.r-tab.active{color:var(--tx-1);border-bottom-color:var(--gold)}
.r-tab-content{display:none;flex:1;overflow-y:auto;padding:12px}
.r-tab-content.active{display:block}

/* ---- CREATE TAB ---- */
#tab-create{display:flex;flex-direction:column;gap:1px}
.f-wrap{
  padding:8px 0;border-bottom:1px solid var(--bd-1);
}
.f-wrap:last-child{border-bottom:none}
.f-lbl{
  display:flex;align-items:center;gap:6px;
  font-family:'JetBrains Mono',monospace;font-size:9px;
  letter-spacing:1px;text-transform:uppercase;
  color:var(--tx-3);margin-bottom:6px;
  user-select:none;
}
.f-lbl.clickable{cursor:pointer;transition:color .15s}
.f-lbl.clickable:hover{color:var(--tx-2)}
.f-dot{width:5px;height:5px;border-radius:50%;flex-shrink:0}
.f-dot.amber{background:var(--amber)}
.f-dot.teal{background:var(--cyan)}
.f-dot.ochre{background:var(--kuro-ochre)}
.f-dot.success{background:var(--green)}
.f-dot.red{background:var(--red)}
.f-dot.cyan{background:var(--cyan)}
.f-arrow{
  margin-left:auto;font-size:8px;transition:transform .2s;
}
.f-arrow.closed{transform:rotate(-90deg)}
.collapsible-body{overflow:hidden;transition:max-height .3s ease}
.prompt-wrap{position:relative}
#prompt{
  width:100%;min-height:70px;padding:8px 10px;
  background:var(--bg-2);border:1px solid var(--bd-2);
  border-radius:var(--r-sm);color:var(--tx-1);
  font-size:12px;line-height:1.5;resize:vertical;outline:none;
  transition:border-color .15s;
}
#prompt:focus{border-color:var(--cyan)}
#prompt::placeholder{color:var(--tx-4);font-size:11px}
.prompt-hint{
  position:absolute;bottom:6px;left:10px;
  font-size:9px;color:var(--tx-4);pointer-events:none;
}
.prompt-counter{
  position:absolute;bottom:6px;right:10px;
  font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--tx-4);
}
.pr-link{
  position:absolute;top:6px;right:8px;
  font-size:9px;color:var(--tx-3);background:none;border:none;
  cursor:pointer;padding:2px 4px;border-radius:2px;
  transition:color .15s;
}
.pr-link:hover{color:var(--tx-1)}
#pr-drop{
  display:none;position:absolute;top:100%;left:0;right:0;
  background:var(--bg-2);border:1px solid var(--bd-2);
  border-radius:var(--r-sm);max-height:120px;overflow-y:auto;z-index:50;
  margin-top:4px;
}
#pr-drop.open{display:block}
.pr-item{
  padding:6px 10px;font-size:11px;color:var(--tx-2);cursor:pointer;
  transition:background .12s;
}
.pr-item:hover{background:var(--bg-3)}
.style-grid{
  display:grid;grid-template-columns:repeat(3,1fr);gap:4px;
  margin-top:4px;
}
.style-btn{
  padding:5px 4px;border-radius:var(--r-sm);
  font-family:'JetBrains Mono',monospace;font-size:9px;
  letter-spacing:.5px;text-transform:uppercase;
  border:1px solid var(--bd-2);background:var(--bg-2);
  color:var(--tx-3);cursor:pointer;transition:all .12s;
}
.style-btn:hover{background:var(--bg-3);color:var(--tx-1)}
.style-btn.active{
  background:rgba(255,215,0,.08);
  border-color:rgba(255,215,0,.3);color:var(--gold-dim);
}
.complexity-row{
  display:flex;align-items:center;justify-content:space-between;
  margin-bottom:6px;
}
.complexity-val{
  font-family:'JetBrains Mono',monospace;font-size:11px;
  color:var(--gold-dim);font-weight:500;
}
#complexity-slider{
  width:100%;appearance:none;-webkit-appearance:none;
  height:3px;background:var(--bg-4);border-radius:2px;outline:none;
}
#complexity-slider::-webkit-slider-thumb{
  -webkit-appearance:none;width:14px;height:14px;
  border-radius:50%;background:var(--gold);cursor:pointer;
  box-shadow:0 0 6px rgba(255,215,0,.4);
}
.shapes-grid{
  display:grid;grid-template-columns:repeat(5,1fr);gap:3px;
  margin-top:4px;
}
.shape-btn{
  display:flex;flex-direction:column;align-items:center;gap:2px;
  padding:5px 2px;border-radius:var(--r-sm);
  border:1px solid var(--bd-1);background:var(--bg-2);
  color:var(--tx-3);cursor:pointer;transition:all .12s;
  font-family:'JetBrains Mono',monospace;font-size:7px;letter-spacing:.5px;
}
.shape-btn svg{width:14px;height:14px;stroke:currentColor;fill:none;stroke-width:1.5}
.shape-btn:hover{background:var(--bg-3);border-color:var(--bd-2);color:var(--tx-1)}
.color-row{display:flex;align-items:center;gap:6px;margin-top:4px;margin-bottom:6px}
.color-preview{
  width:24px;height:24px;border-radius:var(--r-sm);
  border:1px solid var(--bd-2);cursor:pointer;flex-shrink:0;
  transition:border-color .15s;
}
.color-preview:hover{border-color:var(--bd-3)}
#color-picker{opacity:0;width:0;height:0;position:absolute}
.color-hex-inp{
  flex:1;background:var(--bg-2);border:1px solid var(--bd-2);
  border-radius:var(--r-sm);padding:4px 8px;font-size:11px;
  font-family:'JetBrains Mono',monospace;outline:none;
  transition:border-color .15s;color:var(--tx-1);
}
.color-hex-inp:focus{border-color:var(--cyan)}
.swatches-grid{
  display:flex;flex-wrap:wrap;gap:4px;
}
.swatch{
  width:18px;height:18px;border-radius:3px;cursor:pointer;
  border:1px solid transparent;transition:all .12s;
  flex-shrink:0;
}
.swatch.on,.swatch:hover{
  transform:scale(1.1);border-color:rgba(255,255,255,.3);
}
.folder-dropdown{
  width:100%;padding:5px 8px;background:var(--bg-2);
  border:1px solid var(--bd-2);border-radius:var(--r-sm);
  color:var(--tx-1);font-size:11px;outline:none;cursor:pointer;
  transition:border-color .15s;margin-top:4px;
}
.folder-dropdown:focus{border-color:var(--cyan)}

/* ---- PROGRESS ---- */
#progress-sec{
  display:none;padding:10px 0;border-top:1px solid var(--bd-1);
  margin-top:8px;
}
#progress-sec.visible{display:block}
.prog-header{
  display:flex;align-items:center;gap:8px;margin-bottom:8px;
}
.prog-step{font-size:11px;color:var(--tx-2);flex:1}
.prog-pct,.gen-timer-el{
  font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--tx-3);
}
#gen-timer{font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--tx-4)}
.prog-bar-bg{
  height:3px;background:var(--bg-4);border-radius:2px;
  overflow:hidden;margin-bottom:10px;
}
.prog-bar-fill{
  height:100%;width:0%;
  background:linear-gradient(90deg,var(--cyan),var(--gold));
  border-radius:2px;transition:width .3s ease;
}
.pdots{display:flex;gap:4px;margin-bottom:8px}
.pdot-wrap{
  flex:1;display:flex;flex-direction:column;align-items:center;gap:3px;
}
.pdot{
  width:8px;height:8px;border-radius:50%;
  background:var(--bg-4);border:1px solid var(--bd-2);
  transition:all .3s;
}
.pdot.active{background:var(--amber);border-color:var(--amber);box-shadow:0 0 6px rgba(255,165,0,.4)}
.pdot.done{background:var(--cyan);border-color:var(--cyan);box-shadow:0 0 4px rgba(0,212,255,.3)}
.pdot-lbl{
  font-family:'JetBrains Mono',monospace;font-size:7px;
  color:var(--tx-4);letter-spacing:.5px;
}
.log-box{
  max-height:100px;overflow-y:auto;
  font-family:'JetBrains Mono',monospace;font-size:9px;
  line-height:1.5;color:var(--tx-3);
  background:var(--bg-0);border-radius:var(--r-sm);
  padding:6px 8px;
}
.log-line-info{color:var(--tx-3)}
.log-line-gen{color:rgba(0,212,255,.7)}
.log-line-err{color:var(--red)}
.log-line-ok{color:var(--green)}
.err-box{
  display:none;padding:6px 8px;border-radius:var(--r-sm);margin-top:6px;
  background:rgba(255,68,68,.08);border:1px solid rgba(255,68,68,.2);
  font-size:11px;color:var(--red);
}
.err-box.shown{display:block}

/* ---- GENERATE BUTTON ---- */
#gen-btn{
  width:100%;padding:13px;margin-top:12px;
  border-radius:var(--r-sm);
  background:linear-gradient(135deg,var(--amber),var(--gold));
  color:#0a0e17;font-family:'Orbitron',sans-serif;
  font-size:12px;font-weight:700;letter-spacing:3px;
  cursor:pointer;border:none;
  transition:all .15s;position:relative;overflow:hidden;
}
#gen-btn::before{
  content:'';position:absolute;top:0;left:-100%;width:40%;height:100%;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.15),transparent);
  transition:left .4s;
}
#gen-btn:hover::before{left:150%}
#gen-btn:hover{
  box-shadow:0 4px 20px rgba(255,215,0,.35);
  transform:translateY(-1px);
}
#gen-btn:disabled{
  opacity:.5;cursor:not-allowed;transform:none;box-shadow:none;
}
#gen-btn.generating{
  background:linear-gradient(135deg,var(--bg-3),var(--bg-4));
  color:var(--tx-3);
}

/* ---- HISTORY TAB ---- */
#tab-history{padding-bottom:12px}
.hist-header{
  display:flex;align-items:center;justify-content:space-between;
  margin-bottom:10px;
}
.hist-filters{display:flex;flex-wrap:wrap;gap:4px}
.hist-f-btn{
  padding:3px 8px;border-radius:12px;
  font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:1px;
  border:1px solid var(--bd-2);background:var(--bg-2);color:var(--tx-3);
  cursor:pointer;transition:all .12s;
}
.hist-f-btn:hover{background:var(--bg-3);color:var(--tx-1)}
.hist-f-btn.active{
  background:var(--cyan-faint);border-color:rgba(0,212,255,.3);color:var(--cyan-dim);
}
.hist-count{
  font-family:'JetBrains Mono',monospace;font-size:10px;
  color:var(--tx-4);white-space:nowrap;
}
.hist-count em{color:var(--cyan-dim);font-style:normal}
.hist-list{display:flex;flex-direction:column;gap:4px}
.hist-card{
  padding:10px;border-radius:var(--r-sm);
  border:1px solid var(--bd-1);background:var(--bg-2);
  cursor:pointer;transition:all .12s;
  animation:cardSlideIn .2s ease;
}
@keyframes cardSlideIn{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
.hist-card:hover{background:var(--bg-3);border-color:var(--bd-2)}
.hist-card.active{
  border-color:rgba(0,212,255,.3);background:var(--cyan-faint);
}
.hc-top{display:flex;align-items:center;gap:6px;margin-bottom:6px}
.hc-thumb{
  width:28px;height:28px;border-radius:3px;
  background:var(--bg-3);flex-shrink:0;overflow:hidden;
  border:1px solid var(--bd-1);
}
.hc-thumb canvas{width:28px;height:28px}
.hc-prompt{
  flex:1;font-size:11px;color:var(--tx-1);
  overflow:hidden;text-overflow:ellipsis;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;
  line-height:1.4;
}
.hc-del{
  padding:3px;color:var(--tx-4);background:none;border:none;
  cursor:pointer;transition:color .12s;border-radius:3px;flex-shrink:0;
}
.hc-del:hover{color:var(--red);background:rgba(255,68,68,.08)}
.hc-meta{display:flex;align-items:center;gap:6px}
.hc-svc{
  font-family:'JetBrains Mono',monospace;font-size:8px;
  padding:1px 5px;border-radius:2px;
  background:var(--bg-3);border:1px solid var(--bd-1);color:var(--tx-4);
}
.hc-folder{font-size:9px;color:var(--tx-4)}
.hc-date{font-size:9px;color:var(--tx-4);margin-left:auto}
.hist-empty{
  padding:24px;text-align:center;
  font-size:11px;color:var(--tx-4);
}

/* ---- EDIT TAB ---- */
#tab-edit{padding-bottom:12px}
.edit-model-info{
  padding:8px;border-radius:var(--r-sm);
  background:var(--bg-2);border:1px solid var(--bd-2);
  margin-bottom:10px;font-size:11px;color:var(--tx-3);
}
.edit-model-info strong{color:var(--amber)}
#edit-instr{
  width:100%;min-height:60px;padding:8px;
  background:var(--bg-2);border:1px solid var(--bd-2);
  border-radius:var(--r-sm);color:var(--tx-1);
  font-size:12px;resize:vertical;outline:none;
  transition:border-color .15s;margin-top:4px;
}
#edit-instr:focus{border-color:var(--amber)}
#apply-edit-btn{
  width:100%;padding:11px;margin-top:10px;
  border-radius:var(--r-sm);
  background:linear-gradient(135deg,#cc3300,var(--red));
  color:white;font-family:'Orbitron',sans-serif;
  font-size:11px;font-weight:700;letter-spacing:2px;
  cursor:pointer;border:none;transition:all .15s;
}
#apply-edit-btn:hover{box-shadow:0 4px 16px rgba(255,68,68,.3);transform:translateY(-1px)}
#apply-edit-btn:disabled{opacity:.4;cursor:not-allowed;transform:none}
.edit-color-row{display:flex;align-items:center;gap:6px;margin-top:8px}
#edit-progress-sec{
  display:none;margin-top:10px;padding-top:10px;
  border-top:1px solid var(--bd-1);
}
.tag-input-row{display:flex;gap:6px;margin-top:4px}
.tag-input-row input{
  flex:1;padding:5px 8px;background:var(--bg-2);
  border:1px solid var(--bd-2);border-radius:var(--r-sm);
  color:var(--tx-1);font-size:11px;outline:none;
  transition:border-color .15s;
}
.tag-input-row input:focus{border-color:var(--cyan)}
.tag-add-btn{
  padding:5px 10px;border-radius:var(--r-sm);
  font-size:10px;font-weight:600;letter-spacing:1px;
  border:1px solid;cursor:pointer;transition:all .12s;
}
.tag-add-btn.green{
  background:rgba(0,204,136,.08);border-color:rgba(0,204,136,.3);
  color:var(--green);
}
.tag-add-btn.red{
  background:rgba(255,68,68,.08);border-color:rgba(255,68,68,.3);
  color:var(--red);
}
.tags-area{display:flex;flex-wrap:wrap;gap:4px;margin-top:4px;min-height:8px}
.tag-chip{
  display:flex;align-items:center;gap:4px;
  padding:2px 6px;border-radius:10px;font-size:10px;
  border:1px solid;
}
.tag-chip.add-chip{
  background:rgba(0,204,136,.06);border-color:rgba(0,204,136,.2);color:var(--green);
}
.tag-chip.rem-chip{
  background:rgba(255,68,68,.06);border-color:rgba(255,68,68,.2);color:var(--red);
}
.tag-del{font-size:11px;cursor:pointer;opacity:.6;background:none;border:none;color:inherit}
.tag-del:hover{opacity:1}
.mt6{margin-top:6px}

/* ---- EXPORT TAB ---- */
#tab-export{padding-bottom:12px}
.export-info{
  padding:10px;border-radius:var(--r-sm);
  background:var(--bg-2);border:1px solid var(--bd-1);
  margin-bottom:12px;
}
.efi-row{
  display:flex;align-items:center;justify-content:space-between;
  padding:3px 0;font-size:10px;
}
.efi-lbl{color:var(--tx-4);font-family:'JetBrains Mono',monospace;letter-spacing:1px}
.efi-val{color:var(--tx-2);font-family:'JetBrains Mono',monospace}
.export-btn{
  width:100%;padding:10px;border-radius:var(--r-sm);
  font-family:'JetBrains Mono',monospace;font-size:11px;
  letter-spacing:1px;text-transform:uppercase;
  border:1px solid;background:transparent;cursor:pointer;
  transition:all .12s;margin-bottom:6px;
}
.export-btn:hover{background:var(--bg-3)}
.export-btn:disabled{opacity:.4;cursor:not-allowed}
.export-btn.glb{border-color:rgba(0,212,255,.3);color:var(--cyan-dim)}
.export-btn.glb:hover{background:var(--cyan-faint)}
.export-btn.obj{border-color:rgba(255,165,0,.3);color:var(--amber)}
.export-btn.obj:hover{background:rgba(255,165,0,.08)}

/* ---- OTHER PAGES ---- */
#page-gallery,#page-workshop,#page-settings,#page-help{
  padding:24px;overflow-y:auto;flex-direction:column;
}
.page-hdr{
  font-family:'Orbitron',sans-serif;font-size:16px;font-weight:700;
  letter-spacing:3px;color:var(--tx-1);margin-bottom:20px;
  padding-bottom:12px;border-bottom:1px solid var(--bd-1);
}
/* Gallery */
.gal-filters{display:flex;align-items:center;gap:8px;margin-bottom:16px}
.gal-search{
  flex:1;padding:7px 12px;background:var(--bg-2);
  border:1px solid var(--bd-2);border-radius:var(--r-sm);
  color:var(--tx-1);font-size:12px;outline:none;
  transition:border-color .15s;
}
.gal-search:focus{border-color:var(--cyan)}
.gal-search::placeholder{color:var(--tx-4)}
.gal-folder-sel{
  padding:7px 10px;background:var(--bg-2);border:1px solid var(--bd-2);
  border-radius:var(--r-sm);color:var(--tx-1);font-size:11px;outline:none;cursor:pointer;
}
.gal-count{
  font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--tx-4);
  white-space:nowrap;
}
.gal-count em{color:var(--cyan-dim);font-style:normal}
.gal-grid{
  display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;
}
.gal-card{
  border-radius:var(--r-md);overflow:hidden;
  background:var(--bg-2);border:1px solid var(--bd-1);
  cursor:pointer;transition:all .15s;
}
.gal-card:hover{border-color:var(--bd-2);transform:translateY(-2px);box-shadow:0 8px 20px rgba(0,0,0,.3)}
.gal-thumb{
  width:100%;aspect-ratio:1;background:var(--bg-3);
  position:relative;overflow:hidden;
}
.gal-thumb canvas{width:100%;height:100%}
.gal-info{padding:8px}
.gal-prompt{
  font-size:10px;color:var(--tx-2);
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  margin-bottom:3px;
}
.gal-meta{
  display:flex;align-items:center;justify-content:space-between;
  font-size:9px;color:var(--tx-4);
  font-family:'JetBrains Mono',monospace;
}
/* Settings */
.settings-section{margin-bottom:20px}
.settings-section-title{
  font-family:'JetBrains Mono',monospace;font-size:10px;
  letter-spacing:2px;text-transform:uppercase;color:var(--tx-4);
  margin-bottom:10px;padding-bottom:6px;border-bottom:1px solid var(--bd-1);
}
.settings-row{
  display:flex;align-items:center;justify-content:space-between;
  padding:8px 0;border-bottom:1px solid var(--bd-1);
}
.settings-row:last-child{border-bottom:none}
.settings-lbl{font-size:12px;color:var(--tx-2)}
.settings-sub{font-size:10px;color:var(--tx-4);margin-top:1px}
.settings-val{font-size:12px;color:var(--tx-3)}
/* Help */
.help-sec{margin-bottom:16px}
.help-sec-t{
  font-family:'JetBrains Mono',monospace;font-size:10px;
  letter-spacing:2px;text-transform:uppercase;color:var(--amber);
  margin-bottom:8px;
}
.help-row{
  display:flex;gap:8px;padding:5px 0;
  border-bottom:1px solid var(--bd-1);font-size:11px;
}
.help-row:last-child{border-bottom:none}
.help-k{
  font-family:'JetBrains Mono',monospace;color:var(--cyan-dim);
  min-width:80px;flex-shrink:0;
}
.help-v{color:var(--tx-2)}

/* ---- TOAST ---- */
#toast-wrap{
  position:fixed;bottom:20px;right:20px;z-index:99999;
  display:flex;flex-direction:column;gap:8px;
  pointer-events:none;
}
.toast{
  padding:8px 14px;border-radius:var(--r-sm);
  font-size:11px;pointer-events:all;
  border:1px solid;animation:toastIn .2s ease;
  backdrop-filter:blur(8px);
}
@keyframes toastIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.toast.default{background:rgba(26,34,54,.9);border-color:var(--bd-2);color:var(--tx-2)}
.toast.ok{background:rgba(0,204,136,.1);border-color:rgba(0,204,136,.3);color:var(--green)}
.toast.warn{background:rgba(255,165,0,.08);border-color:rgba(255,165,0,.25);color:var(--amber)}
.toast.err{background:rgba(255,68,68,.08);border-color:rgba(255,68,68,.25);color:var(--red)}

/* ---- SAVE MODAL ---- */
.modal-backdrop{
  position:fixed;inset:0;z-index:9000;
  background:rgba(10,14,23,.7);backdrop-filter:blur(4px);
  display:none;align-items:center;justify-content:center;
}
.modal-backdrop.open{display:flex}
.modal{
  width:340px;background:var(--bg-2);
  border:1px solid var(--bd-2);border-radius:var(--r-md);
  padding:20px;
}
.modal-title{
  font-family:'Orbitron',sans-serif;font-size:13px;font-weight:700;
  letter-spacing:2px;margin-bottom:16px;color:var(--tx-1);
}
.modal-body{display:flex;flex-direction:column;gap:10px}
.modal-label{font-size:11px;color:var(--tx-3);margin-bottom:3px}
.modal-inp{
  width:100%;padding:7px 10px;background:var(--bg-3);
  border:1px solid var(--bd-2);border-radius:var(--r-sm);
  color:var(--tx-1);font-size:12px;outline:none;
  transition:border-color .15s;
}
.modal-inp:focus{border-color:var(--cyan)}
.modal-footer{display:flex;gap:8px;justify-content:flex-end;margin-top:16px}
.modal-btn{
  padding:7px 16px;border-radius:var(--r-sm);font-size:12px;
  font-weight:500;cursor:pointer;border:1px solid;transition:all .12s;
}
.modal-btn.cancel{
  border-color:var(--bd-2);background:transparent;color:var(--tx-2);
}
.modal-btn.cancel:hover{background:var(--bg-3);color:var(--tx-1)}
.modal-btn.confirm{
  border-color:rgba(255,215,0,.3);
  background:rgba(255,215,0,.08);color:var(--gold-dim);
}
.modal-btn.confirm:hover{background:rgba(255,215,0,.12);color:var(--gold)}

/* ---- SHORTCUT OVERLAY ---- */
#shortcut-overlay{
  position:fixed;inset:0;z-index:9999;
  background:rgba(10,14,23,.8);backdrop-filter:blur(8px);
  display:none;align-items:center;justify-content:center;
}
#shortcut-overlay.shown{display:flex}
.sc-wrap{
  width:360px;background:var(--bg-2);
  border:1px solid var(--bd-2);border-radius:var(--r-lg);
  padding:24px;
}
.sc-title{
  font-family:'Orbitron',sans-serif;font-size:12px;font-weight:700;
  letter-spacing:3px;color:var(--tx-1);margin-bottom:16px;text-align:center;
}
.sc-grid{display:flex;flex-direction:column;gap:4px}
.sc-row{
  display:flex;align-items:center;gap:10px;padding:5px 0;
  border-bottom:1px solid var(--bd-1);font-size:11px;
}
.sc-row:last-child{border-bottom:none}
.sc-key{
  font-family:'JetBrains Mono',monospace;font-size:9px;
  padding:2px 6px;border-radius:3px;
  background:var(--bg-3);border:1px solid var(--bd-2);
  color:var(--cyan-dim);white-space:nowrap;
}
.sc-desc{color:var(--tx-2)}

/* ---- OFFLINE OVERLAY ---- */
#offline-overlay{
  position:fixed;inset:0;z-index:9998;display:none;
  align-items:center;justify-content:center;
  background:rgba(10,14,23,.9);backdrop-filter:blur(8px);
}
#offline-overlay.shown{display:flex}
.oo-wrap{text-align:center}
.oo-title{
  font-family:'Orbitron',sans-serif;font-size:18px;font-weight:700;
  color:var(--red);margin-bottom:8px;
}
.oo-sub{font-size:13px;color:var(--tx-3);margin-bottom:20px}
.oo-retry{
  padding:8px 20px;border-radius:var(--r-sm);
  background:transparent;border:1px solid var(--bd-2);
  color:var(--tx-2);cursor:pointer;font-size:12px;transition:all .15s;
}
.oo-retry:hover{background:var(--bg-3);color:var(--tx-1)}

/* ---- CONNECTION BAR ---- */
#conn-bar{
  position:fixed;top:0;left:0;right:0;height:2px;
  z-index:99999;pointer-events:none;
}
#conn-bar.live{background:transparent}
#conn-bar.generating{
  background:linear-gradient(90deg,transparent,var(--cyan),var(--gold),transparent);
  animation:connSweep 2s linear infinite;
}
#conn-bar.error{background:var(--red)}
@keyframes connSweep{
  from{background-position:-200% 0}
  to{background-position:200% 0}
}

/* ---- MOBILE ---- */
@media(max-width:768px){
  body{cursor:auto}
  #cursor-dot,#cursor-ring,.cursor-trail{display:none}
  :root{--sidebar-w:100%;--right-w:100%}
  #page-studio{flex-direction:column}
  #studio-left{
    width:100%;height:auto;max-height:200px;
    border-right:none;border-bottom:1px solid var(--bd-1);
  }
  #studio-right{
    width:100%;height:50%;
    border-left:none;border-top:1px solid var(--bd-1);
  }
  #studio-center{flex:1;min-height:200px}
  #nav{
    position:fixed;bottom:0;top:auto;left:0;right:0;width:100%;height:48px;
    flex-direction:row;justify-content:space-around;padding:0 8px;
    border-right:none;border-top:1px solid var(--bd-1);
  }
  #content{left:0;bottom:48px}
  #topbar{left:0}
  #sheet-handle{display:block}
}

/* ---- MISC UTILITIES ---- */
.hidden{display:none!important}
.text-gold{color:var(--gold)}
.text-cyan{color:var(--cyan)}
.text-amber{color:var(--amber)}
.text-red{color:var(--red)}
.text-green{color:var(--green)}
</style>"""

html = html[:style_start] + NEW_CSS + html[style_end:]
print("CSS replaced - " + str(len(NEW_CSS)) + " chars")

# Save
with open(FILE, "w", encoding="utf-8") as f:
    f.write(html)

print("Done! Saved " + FILE)
print("Run: git add . && git commit -m 'Clean UI v2' && git push origin main")
