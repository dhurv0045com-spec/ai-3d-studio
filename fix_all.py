FILE = "static/index.html"
with open(FILE, "r", encoding="utf-8") as f:
    html = f.read()

original = html

# ============================================================
# FIX 1 - Remove !important from max-height so toggleSection works
# ============================================================
html = html.replace(
    "#shapes-body, #color-body, #style-body { overflow: hidden; transition: max-height 0.3s ease; max-height: 0px !important; }",
    "#shapes-body, #color-body, #style-body { overflow: hidden; transition: max-height 0.3s ease; }"
)

# ============================================================
# FIX 2 - Add missing #shell, #pages, #connection-bar CSS
# ============================================================
missing_css = """
/* ---- SHELL + PAGES (critical layout) ---- */
#shell { display: flex; width: 100%; height: 100%; }
#pages { display: flex; flex: 1; overflow: hidden; height: 100%; }
#page-studio { flex-direction: row; }
#page-gallery, #page-workshop, #page-settings, #page-help {
  flex-direction: column; overflow-y: auto; padding: 24px;
}

/* ---- CONNECTION BAR (ID fix) ---- */
#connection-bar {
  position: fixed; top: 0; left: 0; right: 0; height: 2px;
  z-index: 99999; pointer-events: none; background: transparent;
}
#connection-bar.generating {
  background: linear-gradient(90deg, transparent, var(--cyan), var(--gold), transparent);
  background-size: 200% 100%;
  animation: connSweep 2s linear infinite;
}
@keyframes connSweep { from{background-position:200% 0} to{background-position:-200% 0} }
#connection-bar.error { background: var(--red); }

/* ---- LOADING SCREEN wordmark fix ---- */
.ls-wordmark {
  font-family: 'Orbitron', sans-serif; font-size: 28px; font-weight: 900;
  letter-spacing: 6px; color: var(--gold);
  filter: drop-shadow(0 0 12px rgba(255,215,0,.4));
  display: flex; align-items: baseline; gap: 8px;
}
.ls-wordmark span {
  font-size: 11px; letter-spacing: 4px; color: var(--tx-3);
  -webkit-text-fill-color: var(--tx-3);
}
#ls-canvas { position: absolute; inset: 0; z-index: 0; }

/* ---- NAV ICON DOTS (size fix) ---- */
.nav-icon-dots {
  display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 2px;
  width: 14px; height: 14px;
}

/* ---- STUDIO LEFT overflow fix ---- */
#studio-left { overflow-y: auto; }

/* ---- RIGHT PANEL tab content fix ---- */
.r-tab-content {
  display: none; flex: 1; overflow-y: auto; padding: 12px;
  height: calc(100vh - 96px);
}
.r-tab-content.active { display: block; }

/* ---- MODEL BAR ---- */
#model-bar { display: none; }
#model-bar.shown { display: flex !important; }

/* ---- OFFLINE OVERLAY ---- */
#offline-overlay {
  position: fixed; inset: 0; z-index: 9998; display: none;
  align-items: center; justify-content: center;
  background: rgba(10,14,23,.92); flex-direction: column; gap: 16px;
}
#offline-overlay.shown { display: flex; }
.offline-title {
  font-family: 'Orbitron', sans-serif; font-size: 20px;
  font-weight: 700; color: var(--red); letter-spacing: 3px;
}
.offline-sub { font-size: 13px; color: var(--tx-3); }
.offline-dots { display: flex; gap: 8px; }
.offline-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--tx-4); animation: offlinePulse 1.2s infinite;
}
.offline-dot:nth-child(2) { animation-delay: .2s; }
.offline-dot:nth-child(3) { animation-delay: .4s; }
@keyframes offlinePulse { 0%,100%{opacity:.3} 50%{opacity:1} }

/* ---- SHORTCUT OVERLAY ---- */
#shortcut-overlay {
  position: fixed; inset: 0; z-index: 9999; display: none;
  align-items: center; justify-content: center;
  background: rgba(10,14,23,.85); backdrop-filter: blur(8px);
}
#shortcut-overlay.shown { display: flex; }
.sc-box {
  width: 360px; background: var(--bg-2);
  border: 1px solid var(--bd-2); border-radius: var(--r-lg); padding: 24px;
}
.sc-title {
  font-family: 'Orbitron', sans-serif; font-size: 12px; font-weight: 700;
  letter-spacing: 3px; color: var(--tx-1); margin-bottom: 16px; text-align: center;
}
.sc-section {
  font-family: 'JetBrains Mono', monospace; font-size: 9px;
  letter-spacing: 2px; color: var(--amber); text-transform: uppercase;
  margin: 12px 0 6px;
}
.sc-row {
  display: flex; align-items: center; gap: 10px; padding: 5px 0;
  border-bottom: 1px solid var(--bd-1); font-size: 11px;
}
.sc-row:last-of-type { border-bottom: none; }
.sc-key {
  font-family: 'JetBrains Mono', monospace; font-size: 9px;
  padding: 2px 6px; border-radius: 3px;
  background: var(--bg-3); border: 1px solid var(--bd-2);
  color: var(--cyan-dim); white-space: nowrap; min-width: 70px;
}
.sc-desc { color: var(--tx-2); }
.sc-dismiss {
  margin-top: 12px; text-align: center; font-size: 10px; color: var(--tx-4);
  font-family: 'JetBrains Mono', monospace;
}

/* ---- STYLE TOOLTIP ---- */
#style-tooltip {
  position: fixed; z-index: 500; pointer-events: none;
  background: var(--bg-3); border: 1px solid var(--bd-2);
  border-radius: var(--r-sm); padding: 6px 10px;
  font-size: 11px; color: var(--tx-2); display: none;
}
.st-name { font-weight: 600; color: var(--tx-1); margin-bottom: 2px; }
.st-desc { color: var(--tx-3); font-size: 10px; }

/* ---- GALLERY PAGE ---- */
.gal-search {
  width: 100%; padding: 8px 12px; background: var(--bg-2);
  border: 1px solid var(--bd-2); border-radius: var(--r-sm);
  color: var(--tx-1); font-size: 12px; outline: none;
  transition: border-color .15s; margin-bottom: 12px;
}
.gal-search:focus { border-color: var(--cyan); }
.gal-search::placeholder { color: var(--tx-4); }
.gal-folder-sel {
  padding: 6px 10px; background: var(--bg-2); border: 1px solid var(--bd-2);
  border-radius: var(--r-sm); color: var(--tx-1); font-size: 11px;
  outline: none; cursor: pointer; margin-bottom: 12px;
}
.gal-filters { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.gal-count {
  font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--tx-4);
}
.gal-count em { color: var(--cyan-dim); font-style: normal; }
.gal-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 10px;
}
.gal-card {
  border-radius: var(--r-md); background: var(--bg-2);
  border: 1px solid var(--bd-1); cursor: pointer; transition: all .15s; overflow: hidden;
}
.gal-card:hover { border-color: var(--bd-2); transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0,0,0,.3); }
.gal-thumb { width: 100%; aspect-ratio: 1; background: var(--bg-3); }
.gal-info { padding: 8px; }
.gal-prompt { font-size: 10px; color: var(--tx-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.gal-meta { font-size: 9px; color: var(--tx-4); font-family: 'JetBrains Mono', monospace; margin-top: 3px; display: flex; justify-content: space-between; }

/* ---- SETTINGS PAGE ---- */
.settings-section { margin-bottom: 20px; }
.settings-section-title, .settings-sec-title {
  font-family: 'JetBrains Mono', monospace; font-size: 9px;
  letter-spacing: 2px; text-transform: uppercase; color: var(--tx-4);
  margin-bottom: 10px; padding-bottom: 6px; border-bottom: 1px solid var(--bd-1);
}
.settings-row, .settings-row-sub {
  display: flex; align-items: center; justify-content: space-between;
  padding: 9px 0; border-bottom: 1px solid var(--bd-1); font-size: 12px;
}
.settings-row:last-child { border-bottom: none; }
.settings-row-sub { color: var(--tx-2); }
.settings-lbl { color: var(--tx-2); }
.settings-sub { font-size: 10px; color: var(--tx-4); margin-top: 1px; }
.settings-val { font-size: 11px; color: var(--tx-3); font-family: 'JetBrains Mono', monospace; }
.settings-btn {
  padding: 6px 14px; border-radius: var(--r-sm); font-size: 11px;
  border: 1px solid var(--bd-2); background: transparent; color: var(--tx-2);
  cursor: pointer; transition: all .15s;
}
.settings-btn:hover { background: var(--bg-3); color: var(--tx-1); }
.settings-btn.danger { border-color: rgba(255,68,68,.3); color: var(--red); }
.settings-btn.danger:hover { background: rgba(255,68,68,.08); }

/* ---- HELP PAGE ---- */
.help-sec { margin-bottom: 20px; }
.help-sec-t {
  font-family: 'JetBrains Mono', monospace; font-size: 9px;
  letter-spacing: 2px; text-transform: uppercase; color: var(--amber);
  margin-bottom: 8px;
}
.help-row {
  display: flex; gap: 10px; padding: 6px 0;
  border-bottom: 1px solid var(--bd-1); font-size: 11px;
}
.help-row:last-child { border-bottom: none; }
.help-k { font-family: 'JetBrains Mono', monospace; color: var(--cyan-dim); min-width: 80px; flex-shrink: 0; }
.help-v { color: var(--tx-2); }

/* ---- PAGE TITLE ---- */
.page-hdr {
  font-family: 'Orbitron', sans-serif; font-size: 14px; font-weight: 700;
  letter-spacing: 3px; color: var(--tx-1); margin-bottom: 20px;
  padding-bottom: 12px; border-bottom: 1px solid var(--bd-1);
}

/* ---- WORKSHOP PAGE ---- */
.workshop-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px;
}
.workshop-card {
  padding: 16px; background: var(--bg-2); border: 1px solid var(--bd-1);
  border-radius: var(--r-md); cursor: pointer; transition: all .15s;
}
.workshop-card:hover { border-color: var(--bd-2); background: var(--bg-3); }
.workshop-card-title { font-size: 13px; font-weight: 600; color: var(--tx-1); margin-bottom: 6px; }
.workshop-card-desc { font-size: 11px; color: var(--tx-3); line-height: 1.5; }
"""

html = html.replace("</style>", missing_css + "\n</style>", 1)

# ============================================================
# FIX 3 - Rewrite toggleSection to NOT use classList (use inline style directly)
# ============================================================
html = html.replace(
    """function toggleSection(bodyId, arrowId) {
  var el = document.getElementById(bodyId);
  var ar = document.getElementById(arrowId);
  if (!el) return;
  var isOpen = el.style.maxHeight && el.style.maxHeight !== '0px';
  el.style.maxHeight = isOpen ? '0px' : (el.scrollHeight + 400) + 'px';
  el.style.overflow = 'hidden';
  if (ar) ar.style.transform = isOpen ? 'rotate(-90deg)' : 'rotate(0deg)';
}""",
    """function toggleSection(bodyId, arrowId) {
  var el = document.getElementById(bodyId);
  var ar = document.getElementById(arrowId);
  if (!el) return;
  var isOpen = parseInt(el.style.maxHeight || '0') > 0;
  el.style.maxHeight = isOpen ? '0px' : (el.scrollHeight + 500) + 'px';
  el.style.overflow = 'hidden';
  if (ar) ar.style.transform = isOpen ? 'rotate(-90deg)' : 'rotate(0deg)';
}"""
)

# ============================================================
# WRITE
# ============================================================
if html != original:
    with open(FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print("Done! All fixes applied.")
    print("Run: git add . && git commit -m 'Fix layout shell, pages, toggles, icons' && git push origin main")
else:
    print("No changes made")
