import re

FILE = "static/index.html"
print("Reading " + FILE + "...")
with open(FILE, "r", encoding="utf-8") as f:
    html = f.read()

original = html
changes = []

# FIX 1 - Remove Add Features section
html2 = re.sub(
    r'\s*<div class="f-wrap">\s*<div class="f-lbl" style="color:var\(--success\)">.*?Add Features.*?</div>\s*</div>',
    '', html, flags=re.DOTALL)
if html2 != html:
    html = html2
    changes.append("FIX 1: Removed Add Features section")
else:
    print("  WARN: Add Features not found")

# FIX 2 - Remove Remove Features section
html2 = re.sub(
    r'\s*<div class="f-wrap">\s*<div class="f-lbl" style="color:var\(--kube-red\)">.*?Remove Features.*?</div>\s*</div>',
    '', html, flags=re.DOTALL)
if html2 != html:
    html = html2
    changes.append("FIX 2: Removed Remove Features section")
else:
    print("  WARN: Remove Features not found")

# FIX 3 - Make Quick Shapes collapsible header
html2 = re.sub(
    r'<div class="f-lbl"><div class="f-dot teal"></div>Quick Shapes</div>',
    '<div class="f-lbl" onclick="toggleSection(\'shapes-body\',\'shapes-arrow\')" style="cursor:pointer;display:flex;align-items:center;justify-content:space-between;user-select:none"><span style="display:flex;align-items:center;gap:6px"><div class="f-dot teal"></div>Quick Shapes</span><span id="shapes-arrow" style="font-size:9px;color:var(--nolan-cyan);transition:transform 0.2s">&#9660;</span></div>',
    html)
if html2 != html:
    html = html2
    changes.append("FIX 3a: Quick Shapes header collapsible")

# FIX 4 - Make Color section collapsible header
html2 = re.sub(
    r'<div class="f-lbl"><div class="f-dot amber"></div>Color</div>',
    '<div class="f-lbl" onclick="toggleSection(\'color-body\',\'color-arrow\')" style="cursor:pointer;display:flex;align-items:center;justify-content:space-between;user-select:none"><span style="display:flex;align-items:center;gap:6px"><div class="f-dot amber"></div>Color</span><span id="color-arrow" style="font-size:9px;color:var(--tara-amber);transition:transform 0.2s">&#9660;</span></div>',
    html)
if html2 != html:
    html = html2
    changes.append("FIX 4: Color header collapsible")

# FIX 5 - Wrap shapes grid
html2 = re.sub(
    r'(<div class="shapes-grid">)(.*?)(</div>\s*\n\s*</div>\s*\n\s*\n\s*<div class="f-wrap">)',
    r'<div id="shapes-body" style="overflow:hidden;max-height:600px;transition:max-height 0.3s ease">\1\2</div></div></div><div class="f-wrap">',
    html, flags=re.DOTALL, count=1)
if html2 != html:
    html = html2
    changes.append("FIX 5: Shapes grid wrapped in collapsible div")
else:
    print("  WARN: shapes-grid wrap pattern not matched")

# FIX 6 - Wrap color content
html2 = re.sub(
    r'(<div class="color-row">)(.*?)(<div class="swatches-grid" id="swatches"></div>)',
    r'<div id="color-body" style="overflow:hidden;max-height:300px;transition:max-height 0.3s ease">\1\2\3</div>',
    html, flags=re.DOTALL, count=1)
if html2 != html:
    html = html2
    changes.append("FIX 6: Color content wrapped in collapsible div")
else:
    print("  WARN: color-row wrap pattern not matched")

# FIX 7 - Add user avatar to topbar
old7 = '<div class="online-dot" id="online-dot" title="Server connection"></div>'
new7 = ('<div id="user-avatar-wrap" style="display:none;align-items:center;gap:8px;cursor:pointer" '
        'onclick="window.location=\'/auth/logout\'" title="Logout">'
        '<img id="user-avatar" src="" style="width:26px;height:26px;border-radius:50%;'
        'border:1px solid rgba(255,215,0,0.4);object-fit:cover" alt="avatar">'
        '<span id="user-name" style="font-size:10px;font-family:\'JetBrains Mono\',monospace;'
        'color:rgba(255,215,0,0.7);letter-spacing:1px;max-width:100px;overflow:hidden;'
        'text-overflow:ellipsis;white-space:nowrap"></span>'
        '</div>'
        + old7)
if old7 in html:
    html = html.replace(old7, new7, 1)
    changes.append("FIX 7: User avatar added to topbar")
else:
    print("  WARN: online-dot not found")

# FIX 8 - CSS
css = "\n/* COLLAPSIBLE */\n.collapsed{max-height:0!important;}\n.arrow-up{transform:rotate(-90deg)!important;}\n"
if "COLLAPSIBLE" not in html:
    html = html.replace("</style>", css + "</style>", 1)
    changes.append("FIX 8: Collapsible CSS added")

# FIX 9 - JS
js = "\nfunction toggleSection(b,a){var el=document.getElementById(b);var ar=document.getElementById(a);if(!el)return;el.classList.toggle('collapsed');if(ar)ar.classList.toggle('arrow-up');}\nfunction loadUserInfo(){fetch('/auth/me').then(function(r){return r.json();}).then(function(d){if(d.logged_in&&d.user){var w=document.getElementById('user-avatar-wrap');var img=document.getElementById('user-avatar');var nm=document.getElementById('user-name');if(w)w.style.display='flex';if(img&&d.user.picture)img.src=d.user.picture;if(nm&&d.user.name)nm.textContent=d.user.name;}}).catch(function(){});}\ndocument.addEventListener('DOMContentLoaded',loadUserInfo);\n"
if "toggleSection" not in html:
    idx = html.rfind("</script>")
    if idx != -1:
        html = html[:idx] + js + html[idx:]
        changes.append("FIX 9: JS toggleSection + loadUserInfo added")

if html != original:
    with open(FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print("\nDone! " + str(len(changes)) + " fixes applied:")
    for c in changes:
        print("  + " + c)
else:
    print("\nNo changes made - check warnings above")
