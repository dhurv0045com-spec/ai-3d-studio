FILE = "static/index.html"
with open(FILE, "r", encoding="utf-8") as f:
    html = f.read()

original = html

# ============================================================
# THE COMPLETE FIX - All CSS class mismatches + visual polish
# ============================================================

FIX_CSS = """
/* ================================================================
   COMPLETE FIX - Class mismatches, missing styles, visual polish
   ================================================================ */

/* ---- SETTINGS PAGE (HTML uses different classes than CSS) ---- */
.settings-sec {
  margin-bottom: 24px;
  background: var(--bg-2);
  border: 1px solid var(--bd-1);
  border-radius: var(--r-md);
  overflow: hidden;
}
.settings-sec-title {
  display: flex; align-items: center; gap: 8px;
  font-family: 'JetBrains Mono', monospace; font-size: 9px;
  letter-spacing: 2px; text-transform: uppercase; color: var(--tx-3);
  padding: 10px 14px; border-bottom: 1px solid var(--bd-1);
  background: var(--bg-3);
}
.settings-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 14px; border-bottom: 1px solid var(--bd-1);
}
.settings-row:last-child { border-bottom: none; }
.settings-row-l { display: flex; flex-direction: column; gap: 2px; }
.settings-row-lbl { font-size: 12px; color: var(--tx-1); font-weight: 500; }
.settings-row-sub { font-size: 10px; color: var(--tx-4); }
.settings-st {
  display: flex; align-items: center; gap: 6px;
  font-family: 'JetBrains Mono', monospace; font-size: 9px;
  letter-spacing: 1px; padding: 3px 8px; border-radius: 20px;
  border: 1px solid var(--bd-2); color: var(--tx-3);
  background: var(--bg-3);
}
.settings-st.ok { border-color: rgba(0,204,136,.3); color: var(--green); background: rgba(0,204,136,.06); }
.settings-st.warn { border-color: rgba(255,165,0,.3); color: var(--amber); background: rgba(255,165,0,.06); }
.settings-st.info { border-color: rgba(0,212,255,.2); color: var(--cyan-dim); background: var(--cyan-faint); }
.settings-st-dot {
  width: 5px; height: 5px; border-radius: 50%; background: currentColor;
  box-shadow: 0 0 4px currentColor; animation: statusPulse 2s infinite;
}
.settings-btn {
  padding: 5px 12px; border-radius: var(--r-sm); font-size: 10px;
  font-family: 'JetBrains Mono', monospace; letter-spacing: 1px; text-transform: uppercase;
  border: 1px solid var(--bd-2); background: var(--bg-3); color: var(--tx-2);
  cursor: pointer; transition: all .12s;
}
.settings-btn:hover { background: var(--bg-4); color: var(--tx-1); }
.settings-btn.danger { border-color: rgba(255,68,68,.3); color: var(--red); }
.settings-btn.danger:hover { background: rgba(255,68,68,.08); }

/* ---- GALLERY PAGE (HTML uses different classes than CSS) ---- */
.gallery-bar {
  display: flex; align-items: center; gap: 10px;
  padding: 0 0 16px; border-bottom: 1px solid var(--bd-1); margin-bottom: 16px;
  flex-shrink: 0;
}
.gallery-search {
  flex: 1; padding: 7px 12px; background: var(--bg-2);
  border: 1px solid var(--bd-2); border-radius: var(--r-sm);
  color: var(--tx-1); font-size: 12px; outline: none; transition: border-color .15s;
}
.gallery-search:focus { border-color: var(--cyan); }
.gallery-search::placeholder { color: var(--tx-4); }
.gallery-filter {
  padding: 6px 10px; background: var(--bg-2); border: 1px solid var(--bd-2);
  border-radius: var(--r-sm); color: var(--tx-1); font-size: 11px;
  outline: none; cursor: pointer;
}
.gallery-cnt {
  font-family: 'JetBrains Mono', monospace; font-size: 10px;
  color: var(--tx-4); white-space: nowrap;
}
.gallery-cnt em { color: var(--cyan-dim); font-style: normal; }
.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px; overflow-y: auto; flex: 1;
}
.gallery-card {
  border-radius: var(--r-md); overflow: hidden;
  background: var(--bg-2); border: 1px solid var(--bd-1);
  cursor: pointer; transition: all .15s;
}
.gallery-card:hover {
  border-color: var(--bd-3); transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0,0,0,.4);
}
.gallery-empty {
  grid-column: 1 / -1;
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 8px; padding: 60px 24px;
  color: var(--tx-4); text-align: center;
}
.gallery-empty-t {
  font-family: 'Orbitron', sans-serif; font-size: 14px;
  font-weight: 700; letter-spacing: 2px; color: var(--tx-3);
}
.hist-empty-s { font-size: 11px; color: var(--tx-4); }

/* ---- HELP PAGE (HTML uses .help-key, .help-desc) ---- */
.help-key {
  font-family: 'JetBrains Mono', monospace; font-size: 9px;
  padding: 2px 8px; border-radius: 3px;
  background: var(--bg-3); border: 1px solid var(--bd-2);
  color: var(--cyan-dim); white-space: nowrap; min-width: 70px;
  display: inline-block; text-align: center;
}
.help-desc { color: var(--tx-2); font-size: 11px; flex: 1; }

/* ---- EXPORT TAB ---- */
.export-card {
  display: flex; align-items: center; gap: 12px;
  padding: 12px; border-radius: var(--r-sm);
  background: var(--bg-2); border: 1px solid var(--bd-1);
  margin-bottom: 8px; transition: border-color .15s;
}
.export-card:hover { border-color: var(--bd-2); }
.export-icon {
  width: 40px; height: 40px; border-radius: var(--r-sm);
  display: flex; align-items: center; justify-content: center;
  font-family: 'JetBrains Mono', monospace; font-size: 10px;
  font-weight: 700; letter-spacing: 1px; flex-shrink: 0;
}
.export-icon.glb { background: var(--cyan-faint); border: 1px solid rgba(0,212,255,.2); color: var(--cyan-dim); }
.export-icon.obj { background: rgba(255,165,0,.06); border: 1px solid rgba(255,165,0,.2); color: var(--amber); }
.export-icon.fbx { background: rgba(0,204,136,.06); border: 1px solid rgba(0,204,136,.2); color: var(--green); }
.export-info { flex: 1; }
.export-title { font-size: 12px; color: var(--tx-1); font-weight: 500; margin-bottom: 2px; }
.export-sub { font-size: 10px; color: var(--tx-4); }
.export-fileinfo {
  margin-top: 16px; padding: 10px;
  background: var(--bg-2); border: 1px solid var(--bd-1);
  border-radius: var(--r-sm);
}
.efi-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 4px 0; border-bottom: 1px solid var(--bd-1);
}
.efi-row:last-child { border-bottom: none; }
.efi-lbl { font-family: 'JetBrains Mono', monospace; font-size: 9px; color: var(--tx-4); letter-spacing: 1px; }
.efi-val { font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--tx-2); }

/* ---- EDIT TAB MISSING STYLES ---- */
.f-dot.orange { background: #FF6B35; }
.edit-model-box {
  min-height: 60px; padding: 10px; border-radius: var(--r-sm);
  background: var(--bg-2); border: 1px solid var(--bd-1);
  margin-bottom: 10px; font-size: 11px; color: var(--tx-3);
}
.edit-empty-txt { color: var(--tx-4); font-size: 11px; line-height: 1.6; }
#apply-edit-btn {
  width: 100%; padding: 12px; margin-top: 12px;
  border-radius: var(--r-sm);
  background: linear-gradient(135deg, #cc3300, #ff4422);
  color: white; font-family: 'Orbitron', sans-serif;
  font-size: 11px; font-weight: 700; letter-spacing: 3px;
  cursor: pointer; border: none; transition: all .15s;
}
#apply-edit-btn:hover { box-shadow: 0 4px 20px rgba(255,68,34,.4); transform: translateY(-1px); }
#apply-edit-btn:disabled { opacity: .4; cursor: not-allowed; transform: none; box-shadow: none; }
#edit-progress-sec { display: none; margin-top: 12px; padding-top: 10px; border-top: 1px solid var(--bd-1); }

/* ---- NAV ICONS - Replace invisible boxes with actual glyphs ---- */
.nav-icon-wrench::before { content: '⚒'; font-size: 14px; display: block; }
.nav-icon-gear::before { content: '⚙'; font-size: 15px; display: block; }
.nav-icon-wrench, .nav-icon-gear {
  width: auto; height: auto; border: none !important;
  display: flex; align-items: center; justify-content: center;
}

/* ---- TOGGLE ARROWS - Make more visible ---- */
[id$="-arrow"] {
  font-size: 10px !important;
  color: var(--tx-3) !important;
  opacity: 0.8;
  display: inline-block;
  transition: transform 0.25s ease !important;
  margin-left: auto;
  width: 16px;
  text-align: center;
}
[id$="-arrow"]:hover { opacity: 1; }

/* ---- DIRECTOR ZONES: Visual polish ---- */

/* TARANTINO GENERATE BUTTON - Bold, kinetic, dangerous */
#gen-btn {
  position: relative;
  background: linear-gradient(135deg, #e6900a, #FFD700) !important;
  color: #0a0c10 !important;
  font-family: 'Orbitron', sans-serif !important;
  font-size: 11px !important; font-weight: 900 !important;
  letter-spacing: 4px !important;
  padding: 15px !important;
  border-radius: 3px !important;
  box-shadow: 0 0 0 1px rgba(255,215,0,0.3), 0 4px 16px rgba(255,165,0,0.2) !important;
  text-transform: uppercase;
}
#gen-btn:hover {
  box-shadow: 0 0 0 1px rgba(255,215,0,0.6), 0 6px 28px rgba(255,165,0,0.4) !important;
  transform: translateY(-2px) !important;
  letter-spacing: 5px !important;
}
#gen-btn::after {
  content: '';
  position: absolute; inset: 0;
  background: linear-gradient(105deg, transparent 30%, rgba(255,255,255,0.12) 50%, transparent 70%);
  transform: translateX(-100%);
  transition: transform 0.5s ease;
}
#gen-btn:hover::after { transform: translateX(100%); }

/* NOLAN HISTORY CARDS - Layered intelligence */
.hist-card {
  border-left: 2px solid transparent !important;
  transition: all .15s, border-left-color .2s !important;
}
.hist-card:hover { border-left-color: rgba(0,212,255,0.4) !important; }
.hist-card.active { border-left-color: var(--cyan) !important; }

/* VILLENEUVE VIEWPORT - Vast, cinematic depth */
.vp-corner {
  animation: vpCornerPulse 4s ease-in-out infinite alternate;
}
@keyframes vpCornerPulse {
  from { opacity: 0.25; }
  to   { opacity: 0.6; }
}

/* KUBRICK TYPOGRAPHY - Clinical precision */
.f-lbl {
  font-size: 9px !important;
  letter-spacing: 1.5px !important;
  font-weight: 500 !important;
  text-transform: uppercase !important;
}

/* ---- SVC BADGES ---- */
.svc-badge {
  font-family: 'JetBrains Mono', monospace; font-size: 8px;
  padding: 2px 7px; border-radius: 3px; letter-spacing: 1px;
  text-transform: uppercase; font-weight: 500;
  background: var(--bg-3); border: 1px solid var(--bd-2); color: var(--tx-3);
}
.svc-badge.gemini { background: rgba(0,212,255,.08); border-color: rgba(0,212,255,.25); color: var(--cyan-dim); }
.svc-badge.preset { background: rgba(255,165,0,.08); border-color: rgba(255,165,0,.25); color: var(--amber); }
.svc-badge.cache  { background: rgba(123,58,237,.08); border-color: rgba(123,58,237,.25); color: #a78bfa; }
.svc-badge.fallback { background: rgba(255,68,68,.08); border-color: rgba(255,68,68,.25); color: var(--red); }
.svc-badge.shaper { background: rgba(0,204,136,.08); border-color: rgba(0,204,136,.25); color: var(--green); }
.svc-badge.slib { background: rgba(251,113,133,.08); border-color: rgba(251,113,133,.25); color: #fb7185; }

/* ---- PAGE LAYOUT FIXES ---- */
#page-gallery { display: none; flex-direction: column; padding: 20px; overflow: hidden; }
#page-gallery.active { display: flex; }
#page-workshop { display: none; flex-direction: column; overflow-y: auto; padding: 28px; }
#page-workshop.active { display: flex; }
#page-settings { display: none; flex-direction: column; overflow-y: auto; padding: 20px; gap: 0; }
#page-settings.active { display: flex; }
#page-help { display: none; flex-direction: column; overflow-y: auto; }
#page-help.active { display: flex; }

/* ---- TOPBAR GOLD ACCENT ---- */
#topbar {
  border-bottom: 1px solid var(--bd-1) !important;
}
#topbar::after {
  content: '';
  position: absolute; bottom: -1px; left: 48px; right: 0; height: 1px;
  background: linear-gradient(90deg, var(--gold-faint), transparent);
  pointer-events: none;
}

/* ---- STUDIO LEFT SCROLLABLE ---- */
#studio-left { overflow-y: auto !important; }
.r-tab-content {
  height: calc(100% - 38px);
  overflow-y: auto;
}

/* ---- LOADING SCREEN FIX ---- */
#loading-screen {
  position: fixed; inset: 0; z-index: 99999;
  background: var(--bg-0);
  display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 20px;
  transition: opacity .6s, visibility .6s;
}
#loading-screen.gone { opacity: 0; visibility: hidden; pointer-events: none; }

/* ---- MOBILE ---- */
@media (max-width: 768px) {
  body { cursor: auto; }
  #cursor-dot, #cursor-ring, .cursor-trail { display: none !important; }
  #nav {
    position: fixed; bottom: 0; top: auto; left: 0; right: 0;
    width: 100%; height: 50px; flex-direction: row;
    justify-content: space-around; padding: 0;
    border-right: none; border-top: 1px solid var(--bd-1);
  }
  #content { left: 0 !important; bottom: 50px !important; }
  #topbar { left: 0 !important; }
  #page-studio { flex-direction: column; }
  #studio-left { width: 100%; height: 180px; border-right: none; border-bottom: 1px solid var(--bd-1); }
  #studio-right { width: 100%; border-left: none; border-top: 1px solid var(--bd-1); height: 45%; }
  #studio-center { flex: 1; min-height: 200px; }
  #sheet-handle { display: block; }
}
"""

html = html.replace("</style>", FIX_CSS + "\n</style>", 1)
print("CSS injected")

# ============================================================
# Fix toggleSection to be rock solid
# ============================================================
OLD_TS = """function toggleSection(bodyId, arrowId) {
  var el = document.getElementById(bodyId);
  var ar = document.getElementById(arrowId);
  if (!el) return;
  var isOpen = parseInt(el.style.maxHeight || '0') > 0;
  el.style.maxHeight = isOpen ? '0px' : (el.scrollHeight + 500) + 'px';
  el.style.overflow = 'hidden';
  if (ar) ar.style.transform = isOpen ? 'rotate(-90deg)' : 'rotate(0deg)';
}"""

NEW_TS = """function toggleSection(bodyId, arrowId) {
  var el = document.getElementById(bodyId);
  var ar = document.getElementById(arrowId);
  if (!el) return;
  // Read current state from data attribute for reliability
  var isOpen = el.getAttribute('data-open') === '1';
  if (isOpen) {
    el.style.maxHeight = '0px';
    el.setAttribute('data-open', '0');
    if (ar) ar.style.transform = 'rotate(-90deg)';
  } else {
    // Temporarily remove max-height to measure real scrollHeight
    el.style.maxHeight = 'none';
    var h = el.scrollHeight;
    el.style.maxHeight = '0px';
    // Force reflow
    el.offsetHeight;
    el.style.maxHeight = (h + 20) + 'px';
    el.setAttribute('data-open', '1');
    if (ar) ar.style.transform = 'rotate(0deg)';
  }
  el.style.overflow = 'hidden';
  el.style.transition = 'max-height 0.3s ease';
}"""

if OLD_TS in html:
    html = html.replace(OLD_TS, NEW_TS)
    print("toggleSection fixed")
else:
    # inject fresh
    idx = html.rfind("</script>")
    if idx != -1:
        html = html[:idx] + "\n" + NEW_TS + "\n" + html[idx:]
    print("toggleSection injected fresh")

with open(FILE, "w", encoding="utf-8") as f:
    f.write(html)

print("DONE. Now run:")
print("  git add .")
print("  git commit -m 'Fix ALL broken CSS classes, nav icons, toggles, pages'")
print("  git push origin main")
