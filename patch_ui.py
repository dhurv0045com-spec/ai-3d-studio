import re

FILE = "static/index.html"
print("Reading " + FILE + "...")
with open(FILE, "r", encoding="utf-8") as f:
    html = f.read()

original = html
changes = []

# ============================================================
# FIX 1 - Replace cursor with 3D holographic cursor
# ============================================================
old_cursor_css = """#cursor-dot, #cursor-ring {
  position: fixed; border-radius: 50%;
  pointer-events: none; z-index: 999999;
  transform: translate(-50%, -50%);
  transition: opacity .3s;
}
#cursor-dot {
  width: 6px; height: 6px;
  background: #FFD700;
  box-shadow: 0 0 12px #FFD700, 0 0 24px rgba(255,215,0,.6);
  transition: transform .1s ease;
}
#cursor-ring {
  width: 32px; height: 32px;
  border: 1.5px solid rgba(255,215,0,.5);
  backdrop-filter: invert(0);
  transition: width .2s ease, height .2s ease, border-color .2s ease, transform .12s ease;
}
body:has(button:hover) #cursor-ring,
body:has(a:hover) #cursor-ring {
  width: 48px; height: 48px;
  border-color: rgba(255,215,0,.9);
}"""

new_cursor_css = """#cursor-dot, #cursor-ring, #cursor-trail-wrap {
  position: fixed;
  pointer-events: none; z-index: 999999;
  transform: translate(-50%, -50%);
}
#cursor-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: #FFD700;
  box-shadow: 0 0 8px #FFD700, 0 0 20px rgba(255,215,0,.8), 0 0 40px rgba(255,215,0,.3);
  transition: transform .08s ease, background .2s;
}
#cursor-ring {
  width: 36px; height: 36px;
  border-radius: 50%;
  border: 1px solid rgba(0,212,255,.6);
  box-shadow: 0 0 8px rgba(0,212,255,.3), inset 0 0 8px rgba(0,212,255,.1);
  transition: width .15s, height .15s, border-color .15s, transform .12s;
}
#cursor-ring::before {
  content:'';
  position:absolute;
  inset:4px;
  border-radius:50%;
  border:1px solid rgba(255,215,0,.2);
}
#cursor-ring::after {
  content:'';
  position:absolute;
  top:50%; left:-6px;
  width:6px; height:1px;
  background: rgba(0,212,255,.5);
  box-shadow: calc(100% + 6px) 0 0 rgba(0,212,255,.5);
}
.cursor-trail {
  position:fixed;
  border-radius:50%;
  pointer-events:none;
  z-index:999998;
  transform:translate(-50%,-50%);
  background:rgba(0,212,255,.4);
  transition:opacity .3s;
}
body:has(button:hover) #cursor-ring,
body:has(a:hover) #cursor-ring {
  width: 52px; height: 52px;
  border-color: rgba(255,215,0,.9);
  box-shadow: 0 0 16px rgba(255,215,0,.4);
}
body:has(button:hover) #cursor-dot,
body:has(a:hover) #cursor-dot {
  background: #00D4FF;
  box-shadow: 0 0 8px #00D4FF, 0 0 20px rgba(0,212,255,.8);
}"""

if old_cursor_css in html:
    html = html.replace(old_cursor_css, new_cursor_css, 1)
    changes.append("FIX 1: 3D holographic cursor CSS")
else:
    print("  WARN FIX1: cursor CSS not found")

# ============================================================
# FIX 2 - Replace cursor JS with trail version
# ============================================================
old_cursor_js = """/* ── CUSTOM CURSOR ─────────────────────────────────────────── */
(function() {
  var dot  = document.getElementById('cursor-dot');
  var ring = document.getElementById('cursor-ring');
  if (!dot || !ring) return;
  var mx=0,my=0, rx=0,ry=0;
  document.addEventListener('mousemove', function(e) {
    mx = e.clientX; my = e.clientY;
    dot.style.left  = mx + 'px';
    dot.style.top   = my + 'px';
  });
  (function lerp() {
    rx += (mx - rx) * 0.12;
    ry += (my - ry) * 0.12;
    ring.style.left = rx + 'px';
    ring.style.top  = ry + 'px';
    requestAnimationFrame(lerp);
  })();
  // Cursor states
  document.addEventListener('mousedown', function() {
    dot.style.transform  = 'translate(-50%,-50%) scale(0.5)';
    ring.style.transform = 'translate(-50%,-50%) scale(0.8)';
  });
  document.addEventListener('mouseup', function() {
    dot.style.transform  = 'translate(-50%,-50%) scale(1)';
    ring.style.transform = 'translate(-50%,-50%) scale(1)';
  });
  // Expand ring on interactive elements
  document.addEventListener('mouseover', function(e) {
    var el = e.target.closest('button,a,[onclick],.folder-row,.hist-card,.gal-card,.shape-btn,.style-btn,.swatch,.nav-item');
    if (el) {
      ring.style.width  = '52px';
      ring.style.height = '52px';
      ring.style.borderColor = 'rgba(255,215,0,.8)';
    }
  });
  document.addEventListener('mouseout', function(e) {
    var el = e.target.closest('button,a,[onclick],.folder-row,.hist-card,.gal-card,.shape-btn,.style-btn,.swatch,.nav-item');
    if (el) {
      ring.style.width  = '32px';
      ring.style.height = '32px';
      ring.style.borderColor = 'rgba(255,215,0,.5)';
    }
  });
})();"""

new_cursor_js = """/* ── 3D HOLOGRAPHIC CURSOR ──────────────────────────────────── */
(function() {
  var dot  = document.getElementById('cursor-dot');
  var ring = document.getElementById('cursor-ring');
  if (!dot || !ring) return;
  if ('ontouchstart' in window) { dot.style.display='none'; ring.style.display='none'; return; }
  document.body.style.cursor = 'none';
  var mx=0,my=0,rx=0,ry=0;
  // Trail dots
  var trails = [];
  var TRAIL_COUNT = 8;
  for (var i=0;i<TRAIL_COUNT;i++) {
    var t = document.createElement('div');
    t.className = 'cursor-trail';
    var sz = 6 - i*0.5;
    t.style.cssText = 'width:'+sz+'px;height:'+sz+'px;opacity:0;';
    document.body.appendChild(t);
    trails.push({el:t, x:0, y:0});
  }
  document.addEventListener('mousemove', function(e) {
    mx = e.clientX; my = e.clientY;
    dot.style.left = mx+'px'; dot.style.top = my+'px';
  });
  // Rotation angle for ring
  var angle = 0;
  (function loop() {
    rx += (mx-rx)*0.12; ry += (my-ry)*0.12;
    ring.style.left=rx+'px'; ring.style.top=ry+'px';
    angle += 1.2;
    ring.style.transform = 'translate(-50%,-50%) rotate('+angle+'deg)';
    // Update trails
    for (var i=trails.length-1;i>0;i--) {
      trails[i].x += (trails[i-1].x - trails[i].x)*0.35;
      trails[i].y += (trails[i-1].y - trails[i].y)*0.35;
      var op = (1-(i/trails.length))*0.35;
      trails[i].el.style.left=trails[i].x+'px';
      trails[i].el.style.top=trails[i].y+'px';
      trails[i].el.style.opacity=op;
    }
    trails[0].x=mx; trails[0].y=my;
    requestAnimationFrame(loop);
  })();
  document.addEventListener('mousedown', function() {
    dot.style.transform='translate(-50%,-50%) scale(0.4)';
    ring.style.transform='translate(-50%,-50%) scale(0.75)';
  });
  document.addEventListener('mouseup', function() {
    dot.style.transform='translate(-50%,-50%) scale(1)';
  });
})();"""

if old_cursor_js in html:
    html = html.replace(old_cursor_js, new_cursor_js, 1)
    changes.append("FIX 2: 3D cursor with rotating ring and trail")
else:
    print("  WARN FIX2: cursor JS block not found")

# ============================================================
# FIX 3 - Add login overlay modal + CSS + JS
# ============================================================
login_modal_css = """
/* ── LOGIN OVERLAY ─────────────────────────────────────────── */
#login-overlay {
  position:fixed;inset:0;z-index:99998;
  display:flex;align-items:center;justify-content:center;
  background:rgba(1,8,20,0.92);
  backdrop-filter:blur(12px);
  -webkit-backdrop-filter:blur(12px);
}
#login-overlay.hidden { display:none; }
#login-overlay canvas#ol-stars {
  position:absolute;inset:0;z-index:0;pointer-events:none;
}
#login-overlay canvas#ol-grid {
  position:absolute;inset:0;z-index:1;pointer-events:none;
}
#login-card {
  position:relative;z-index:2;
  width:400px;
  background:rgba(4,12,26,0.9);
  border:1px solid rgba(255,215,0,0.25);
  border-top:2px solid #FFD700;
  padding:44px 36px 36px;
  animation:loginCardIn .6s cubic-bezier(.16,1,.3,1);
}
@keyframes loginCardIn{from{opacity:0;transform:translateY(24px) scale(.97)}to{opacity:1;transform:none}}
#login-card::before{
  content:'';position:absolute;top:0;left:-100%;width:50%;height:2px;
  background:linear-gradient(90deg,transparent,#FFD700,transparent);
  animation:loginShimmer 2.5s ease-in-out infinite;
}
@keyframes loginShimmer{0%{left:-100%}100%{left:200%}}
.lc-corner{position:absolute;width:10px;height:10px;}
.lc-tl{top:-1px;left:-1px;border-top:2px solid #00D4FF;border-left:2px solid #00D4FF;}
.lc-tr{top:-1px;right:-1px;border-top:2px solid #00D4FF;border-right:2px solid #00D4FF;}
.lc-bl{bottom:-1px;left:-1px;border-bottom:2px solid #00D4FF;border-left:2px solid #00D4FF;}
.lc-br{bottom:-1px;right:-1px;border-bottom:2px solid #00D4FF;border-right:2px solid #00D4FF;}
#login-card .lc-logo{
  font-family:'Orbitron',sans-serif;font-size:36px;font-weight:900;
  letter-spacing:6px;text-align:center;
  background:linear-gradient(135deg,#FFD700,#fff,#FFA500);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
  filter:drop-shadow(0 0 12px rgba(255,215,0,.4));
  margin-bottom:4px;
}
#login-card .lc-sub{
  text-align:center;font-family:'JetBrains Mono',monospace;
  font-size:10px;letter-spacing:5px;color:rgba(0,212,255,.6);
  text-transform:uppercase;margin-bottom:24px;
}
#login-card .lc-divider{
  height:1px;background:linear-gradient(90deg,transparent,#FFD700,transparent);
  margin:0 0 24px;position:relative;
}
#login-card .lc-divider::before{
  content:'◆';position:absolute;left:50%;top:50%;
  transform:translate(-50%,-50%);color:#FFD700;font-size:7px;
  background:rgba(4,12,26,0.9);padding:0 8px;
}
.lc-btn{
  width:100%;padding:13px 16px;border:none;border-radius:2px;
  font-family:'Rajdhani',sans-serif;font-size:13px;font-weight:600;
  letter-spacing:3px;text-transform:uppercase;
  cursor:pointer;position:relative;overflow:hidden;
  display:flex;align-items:center;justify-content:center;gap:8px;
  transition:transform .15s,box-shadow .15s;
  text-decoration:none;
}
.lc-btn:hover{transform:translateY(-1px);}
.lc-btn::before{
  content:'';position:absolute;top:0;left:-100%;width:40%;height:100%;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.08),transparent);
  transition:left .3s;
}
.lc-btn:hover::before{left:150%;}
#lc-google{
  background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.12);
  color:rgba(255,255,255,.8);margin-bottom:10px;
}
#lc-google:hover{background:rgba(255,255,255,.09);border-color:rgba(255,255,255,.25);}
#lc-guest{
  background:linear-gradient(135deg,#FFA500,#FFD700);
  color:#010814;font-weight:700;
}
#lc-guest:hover{box-shadow:0 4px 20px rgba(255,215,0,.4);}
.lc-sep{
  display:flex;align-items:center;gap:10px;margin:12px 0;
  font-family:'JetBrains Mono',monospace;font-size:9px;
  color:rgba(255,255,255,.18);letter-spacing:2px;
}
.lc-sep::before,.lc-sep::after{content:'';flex:1;height:1px;background:rgba(255,255,255,.07);}
#lc-status{
  margin-top:20px;text-align:center;
  font-family:'JetBrains Mono',monospace;font-size:9px;
  color:rgba(0,212,255,.4);letter-spacing:2px;
  display:flex;align-items:center;justify-content:center;gap:6px;
}
#lc-status-dot{width:5px;height:5px;border-radius:50%;background:#00D4FF;
  box-shadow:0 0 6px #00D4FF;animation:lcPulse 2s infinite;}
@keyframes lcPulse{0%,100%{opacity:1}50%{opacity:.3}}
#login-overlay .ol-sig{
  position:absolute;bottom:16px;right:20px;
  font-family:'JetBrains Mono',monospace;font-size:10px;
  color:rgba(255,215,0,.2);letter-spacing:2px;z-index:3;
  transition:color .3s;
}
#login-overlay .ol-sig:hover{color:rgba(255,215,0,.7);}
"""

if "login-overlay" not in html:
    html = html.replace("</style>", login_modal_css + "\n</style>", 1)
    changes.append("FIX 3: Login overlay CSS added")

# ============================================================
# FIX 4 - Add login overlay HTML before </body>
# ============================================================
login_modal_html = """
<!-- ======= LOGIN OVERLAY ======= -->
<div id="login-overlay">
  <canvas id="ol-stars"></canvas>
  <canvas id="ol-grid"></canvas>
  <div id="login-card">
    <div class="lc-corner lc-tl"></div>
    <div class="lc-corner lc-tr"></div>
    <div class="lc-corner lc-bl"></div>
    <div class="lc-corner lc-br"></div>
    <div class="lc-logo">AUREX 3D</div>
    <div class="lc-sub">3D STUDIO &middot; V7</div>
    <div class="lc-divider"></div>
    <a href="/auth/google" class="lc-btn" id="lc-google">
      <svg width="16" height="16" viewBox="0 0 48 48"><path fill="#FFC107" d="M43.6 20H42v-.1H24v8h11.3C33.6 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 8 3l5.7-5.7C34 6.1 29.3 4 24 4 13 4 4 13 4 24s9 20 20 20 20-9 20-20c0-1.3-.1-2.7-.4-4z"/><path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 8 3l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"/><path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-7.9l-6.5 5C9.5 39.6 16.2 44 24 44z"/><path fill="#1976D2" d="M43.6 20H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.7-.4-4z"/></svg>
      Continue with Google
    </a>
    <div class="lc-sep">or</div>
    <button class="lc-btn" id="lc-guest" onclick="guestLogin()">Enter as Guest</button>
    <div id="lc-status"><div id="lc-status-dot"></div><span>STUDIO ONLINE</span></div>
  </div>
  <div class="ol-sig">// Ankit raj</div>
</div>
"""

if "login-overlay" not in html or "login-card" not in html:
    html = html.replace("</body>", login_modal_html + "\n</body>", 1)
    changes.append("FIX 4: Login overlay HTML added")

# ============================================================
# FIX 5 - Add folder collapse button to left panel header
# ============================================================
old_workspace = """        <div class="sec-head">
          <div class="sec-dot ochre"></div>
          Workspace
        </div>
        <div class="folder-sec">"""
new_workspace = """        <div class="sec-head" style="display:flex;align-items:center;justify-content:space-between;cursor:pointer" onclick="toggleSection('folder-panel-body','folder-panel-arrow')">
          <span style="display:flex;align-items:center;gap:6px"><div class="sec-dot ochre"></div>Workspace</span>
          <span id="folder-panel-arrow" style="font-size:9px;color:var(--kuro-ochre);transition:transform 0.2s">&#9660;</span>
        </div>
        <div id="folder-panel-body" style="overflow:hidden;max-height:600px;transition:max-height 0.3s ease">
        <div class="folder-sec">"""
if old_workspace in html:
    html = html.replace(old_workspace, new_workspace, 1)
    # close the wrapper after folder-sec
    old_close = """          </div>
        </div>

        <div class="options-sec">"""
    new_close = """          </div>
        </div>
        </div><!-- end folder-panel-body -->

        <div class="options-sec">"""
    if old_close in html:
        html = html.replace(old_close, new_close, 1)
    changes.append("FIX 5: Folder panel collapse added")
else:
    print("  WARN FIX5: Workspace header not found")

# ============================================================
# FIX 6 - Add login overlay JS + fix toggleSection + guest login
# ============================================================
login_js = """
/* ── LOGIN OVERLAY ─────────────────────────────────────────── */
function initLoginOverlay() {
  fetch('/auth/me').then(function(r){return r.json();}).then(function(d){
    var ov = document.getElementById('login-overlay');
    if (!ov) return;
    if (d.logged_in) {
      ov.classList.add('hidden');
      // Show user avatar
      var w=document.getElementById('user-avatar-wrap');
      var img=document.getElementById('user-avatar');
      var nm=document.getElementById('user-name');
      if(w) w.style.display='flex';
      if(img&&d.user&&d.user.picture) img.src=d.user.picture;
      if(nm&&d.user&&d.user.name) nm.textContent=d.user.name;
    } else {
      ov.classList.remove('hidden');
      initOverlayCanvas();
    }
  }).catch(function(){
    // If auth fails, still show overlay
    var ov=document.getElementById('login-overlay');
    if(ov) { ov.classList.remove('hidden'); initOverlayCanvas(); }
  });
}

function guestLogin() {
  fetch('/guest').then(function(){
    var ov=document.getElementById('login-overlay');
    if(ov) ov.classList.add('hidden');
    var nm=document.getElementById('user-name');
    if(nm) nm.textContent='Guest';
  }).catch(function(){
    var ov=document.getElementById('login-overlay');
    if(ov) ov.classList.add('hidden');
  });
}

function initOverlayCanvas() {
  // Stars
  var sc = document.getElementById('ol-stars');
  if (!sc) return;
  sc.width = window.innerWidth; sc.height = window.innerHeight;
  var sCtx = sc.getContext('2d');
  var stars = [];
  for (var i=0;i<150;i++) {
    stars.push({x:Math.random()*sc.width,y:Math.random()*sc.height,
      r:Math.random()*1.2+0.3,speed:Math.random()*.02+.005,phase:Math.random()*Math.PI*2});
  }
  // Grid
  var gc = document.getElementById('ol-grid');
  gc.width=window.innerWidth; gc.height=window.innerHeight;
  var gCtx=gc.getContext('2d');
  var gOff=0;
  function drawOlGrid() {
    var W=gc.width,H=gc.height;
    gCtx.clearRect(0,0,W,H);
    var hy=H*0.5;
    var vp={x:W/2,y:hy};
    gOff=(gOff+0.3)%60;
    gCtx.save();
    gCtx.shadowColor='#00D4FF'; gCtx.shadowBlur=3;
    for(var c=-20;c<=20;c++){
      var bx=W/2+c*(W/20);
      var al=Math.max(0,0.4-Math.abs(c)/20*0.35);
      gCtx.beginPath();gCtx.moveTo(vp.x,vp.y);gCtx.lineTo(bx,H);
      gCtx.strokeStyle='rgba(0,212,255,'+al+')';gCtx.lineWidth=c===0?1:0.4;gCtx.stroke();
    }
    for(var r=0;r<=16;r++){
      var prog=(r+(gOff/60))/16;
      var y=hy+Math.pow(prog,2)*(H-hy);
      if(y<hy) continue;
      var dt=(y-hy)/(H-hy);
      var lw=W*0.4+dt*W*0.7;
      gCtx.beginPath();gCtx.moveTo(vp.x-lw/2,y);gCtx.lineTo(vp.x+lw/2,y);
      gCtx.strokeStyle='rgba(0,180,220,'+(dt*0.5)+')';
      gCtx.lineWidth=r%3===0?0.8:0.3;gCtx.stroke();
    }
    // Horizon glow
    gCtx.beginPath();gCtx.moveTo(0,hy);gCtx.lineTo(W,hy);
    var hg=gCtx.createLinearGradient(0,hy,W,hy);
    hg.addColorStop(0,'transparent');hg.addColorStop(.4,'rgba(0,212,255,.4)');
    hg.addColorStop(.5,'rgba(255,215,0,.6)');hg.addColorStop(.6,'rgba(0,212,255,.4)');hg.addColorStop(1,'transparent');
    gCtx.strokeStyle=hg;gCtx.lineWidth=1.5;gCtx.shadowColor='#FFD700';gCtx.shadowBlur=10;gCtx.stroke();
    gCtx.restore();
  }
  var t=0;
  function olLoop() {
    // Stars
    sCtx.clearRect(0,0,sc.width,sc.height);
    t+=0.016;
    stars.forEach(function(s){
      var a=0.3+0.7*Math.abs(Math.sin(t*s.speed+s.phase));
      sCtx.beginPath();sCtx.arc(s.x,s.y,s.r,0,Math.PI*2);
      sCtx.fillStyle='rgba(255,255,255,'+a+')';sCtx.fill();
    });
    drawOlGrid();
    var ov=document.getElementById('login-overlay');
    if(ov && !ov.classList.contains('hidden')) requestAnimationFrame(olLoop);
  }
  requestAnimationFrame(olLoop);
  // Mouse parallax on card
  var card=document.getElementById('login-card');
  document.getElementById('login-overlay').addEventListener('mousemove',function(e){
    if(!card) return;
    var cx=window.innerWidth/2, cy=window.innerHeight/2;
    var dx=(e.clientX-cx)/(window.innerWidth/2);
    var dy=(e.clientY-cy)/(window.innerHeight/2);
    card.style.transform='perspective(600px) rotateY('+(dx*6)+'deg) rotateX('+(-dy*6)+'deg)';
  });
}

document.addEventListener('DOMContentLoaded', function(){
  initLoginOverlay();
  if (typeof loadUserInfo === 'function') loadUserInfo();
});
"""

if "initLoginOverlay" not in html:
    idx = html.rfind("</script>")
    if idx != -1:
        html = html[:idx] + login_js + "\n" + html[idx:]
        changes.append("FIX 6: Login overlay JS + guest login + canvas animation")

# ============================================================
# WRITE
# ============================================================
if html != original:
    with open(FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print("\nDone! " + str(len(changes)) + " fixes applied:")
    for c in changes:
        print("  + " + c)
else:
    print("\nNo changes - check warnings")
