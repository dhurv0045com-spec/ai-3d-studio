FILE = "static/index.html"
with open(FILE, "r", encoding="utf-8") as f:
    html = f.read()

original = html

# Inject nav + page + toggle fix CSS right before </style>
fix_css = """
/* ---- NAV FIXES ---- */
nav#nav { display: flex !important; }
.nav-items { display: flex; flex-direction: column; gap: 2px; width: 100%; align-items: center; }
.nav-icon-dots { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 2px; width: 14px; }
.nav-icon-dots span { width: 4px; height: 4px; background: currentColor; border-radius: 1px; display: block; }
.nav-icon-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 2px; width: 12px; }
.nav-icon-grid span { width: 5px; height: 5px; background: currentColor; border-radius: 1px; display: block; }
.nav-icon-wrench { width: 14px; height: 14px; border: 1.5px solid currentColor; border-radius: 2px; position: relative; }
.nav-icon-wrench::before { content: ''; position: absolute; top: 50%; left: -4px; width: 4px; height: 1.5px; background: currentColor; }
.nav-icon-wrench::after { content: ''; position: absolute; top: 50%; right: -4px; width: 4px; height: 1.5px; background: currentColor; }
.nav-icon-gear { width: 14px; height: 14px; border: 2px solid currentColor; border-radius: 50%; position: relative; }
.nav-icon-gear::before { content: '⚙'; font-size: 13px; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: currentColor; border: none; }
.nav-icon-q { font-size: 14px; font-weight: 700; color: currentColor; }

/* ---- PAGE FIXES ---- */
.page { display: none !important; width: 100%; height: 100%; }
.page.active { display: flex !important; }
#page-studio { flex-direction: row !important; }
#page-gallery { flex-direction: column !important; overflow-y: auto !important; padding: 20px !important; }
#page-workshop { flex-direction: column !important; overflow-y: auto !important; padding: 20px !important; }
#page-settings { flex-direction: column !important; overflow-y: auto !important; padding: 20px !important; }
#page-help { flex-direction: column !important; overflow-y: auto !important; padding: 20px !important; }

/* ---- COLLAPSIBLE TOGGLE FIX ---- */
.collapsible-body { overflow: hidden; transition: max-height 0.3s ease; }
#shapes-body, #color-body, #style-body { overflow: hidden; transition: max-height 0.3s ease; max-height: 0px !important; }
#folder-panel-body { overflow: hidden; transition: max-height 0.3s ease; max-height: 600px; }

/* f-arrow visibility */
.f-lbl .f-arrow, .f-lbl span[id$="-arrow"] {
  margin-left: auto;
  font-size: 9px;
  color: var(--tx-3);
  transition: transform 0.2s;
  display: inline-block;
}
.sec-head .sec-arrow {
  margin-left: auto;
  font-size: 9px;
  transition: transform 0.2s;
}

/* ---- STUDIO LEFT SCROLL ---- */
#studio-left { overflow-y: auto; }
#studio-left-scroll { display: block; }

/* ---- RIGHT PANEL SCROLL ---- */
.r-tab-content { overflow-y: auto; height: calc(100% - 36px); }

/* ---- SETTINGS PAGE ---- */
.settings-sec-title, .settings-section-title {
  font-family: 'JetBrains Mono', monospace; font-size: 9px;
  letter-spacing: 2px; text-transform: uppercase;
  color: var(--tx-4); margin-bottom: 10px;
  padding-bottom: 6px; border-bottom: 1px solid var(--bd-1);
}
.settings-row { display: flex; align-items: center; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid var(--bd-1); }
.settings-row:last-child { border-bottom: none; }

/* ---- FIX MODEL BAR ---- */
#model-bar { display: none; }
#model-bar.shown { display: flex; }
"""

html = html.replace("</style>", fix_css + "\n</style>", 1)

with open(FILE, "w", encoding="utf-8") as f:
    f.write(html)

print("Done! Nav, pages, toggles fixed.")
print("Run: git add . && git commit -m 'Fix nav icons, pages, toggles' && git push origin main")
