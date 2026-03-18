import re

FILE = "static/index.html"
print("Reading " + FILE + "...")
with open(FILE, "r", encoding="utf-8") as f:
    html = f.read()

original = html
changes = []

# ============================================================
# FIX 1 - Make shapes-body, color-body, style-body CLOSED by default
# ============================================================
# Set max-height to 0 by default (closed)
for body_id in ['shapes-body', 'color-body', 'style-body']:
    html = re.sub(
        r'id="' + body_id + r'" style="[^"]*"',
        'id="' + body_id + '" style="max-height:0px;overflow:hidden;transition:max-height 0.3s ease"',
        html, count=1)
# Rotate arrows to show closed state by default
for arrow_id in ['shapes-arrow', 'color-arrow', 'style-arrow']:
    html = re.sub(
        r'id="' + arrow_id + r'" style="[^"]*"',
        'id="' + arrow_id + '" style="font-size:9px;transition:transform 0.2s;transform:rotate(-90deg)"',
        html, count=1)
changes.append("FIX 1: Shapes/Color/Style sections closed by default")

# ============================================================
# FIX 2 - Make folder-panel-body OPEN by default but add toggle
# ============================================================
html = re.sub(
    r'id="folder-panel-body" style="[^"]*"',
    'id="folder-panel-body" style="max-height:600px;overflow:hidden;transition:max-height 0.3s ease"',
    html, count=1)
changes.append("FIX 2: Folder panel open by default with toggle")

# ============================================================
# FIX 3 - Clean up toggleSection to be rock solid
# ============================================================
new_toggle = """
function toggleSection(bodyId, arrowId) {
  var el = document.getElementById(bodyId);
  var ar = document.getElementById(arrowId);
  if (!el) return;
  var isOpen = el.style.maxHeight && el.style.maxHeight !== '0px';
  el.style.maxHeight = isOpen ? '0px' : (el.scrollHeight + 400) + 'px';
  el.style.overflow = 'hidden';
  if (ar) ar.style.transform = isOpen ? 'rotate(-90deg)' : 'rotate(0deg)';
}
"""
# Remove all existing toggleSection definitions and replace
html = re.sub(r'function toggleSection\s*\([^)]*\)\s*\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', '', html)
idx = html.rfind("</script>")
if idx != -1:
    html = html[:idx] + new_toggle + html[idx:]
changes.append("FIX 3: toggleSection rewritten clean")

# ============================================================
# FIX 4 - User info: completely rewrite loadUserInfo
# ============================================================
new_lui = """
function loadUserInfo() {
  fetch('/auth/me').then(function(r) { return r.json(); }).then(function(d) {
    var wrap = document.getElementById('user-avatar-wrap');
    var img  = document.getElementById('user-avatar');
    var nm   = document.getElementById('user-name');
    var em   = document.getElementById('user-email');
    if (d.logged_in && d.user) {
      if (wrap) wrap.style.display = 'flex';
      if (img && d.user.picture) img.src = d.user.picture;
      if (nm)  nm.textContent  = d.user.name  || 'User';
      if (em)  em.textContent  = d.user.email || '';
    }
  }).catch(function() {});
}
"""
html = re.sub(r'function loadUserInfo\s*\(\s*\)\s*\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', '', html, flags=re.DOTALL)
idx = html.rfind("</script>")
if idx != -1:
    html = html[:idx] + new_lui + html[idx:]
changes.append("FIX 4: loadUserInfo rewritten clean")

# ============================================================
# FIX 5 - User avatar HTML: add email span if missing
# ============================================================
if 'user-email' not in html:
    html = re.sub(
        r'(<span id="user-name"[^>]+></span>)',
        r'\1<span id="user-email" style="font-size:8px;font-family:\'JetBrains Mono\',monospace;color:rgba(255,255,255,0.35);max-width:130px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;display:block"></span>',
        html, count=1)
    changes.append("FIX 5: Email span added to topbar user info")

# ============================================================
# FIX 6 - Force login overlay visible, hide only when logged in
# Remove all existing initLoginOverlay and reinject clean version
# ============================================================
clean_login_js = """
function initLoginOverlay() {
  var ov = document.getElementById('login-overlay');
  if (!ov) return;
  // Always show first
  ov.style.display = 'flex';
  ov.classList.remove('hidden');
  // Then check if logged in
  fetch('/auth/me').then(function(r) { return r.json(); }).then(function(d) {
    if (d.logged_in && d.user && d.user.sub && d.user.sub !== 'anonymous') {
      ov.style.display = 'none';
      ov.classList.add('hidden');
      loadUserInfo();
    } else {
      initOverlayCanvas();
    }
  }).catch(function() {
    initOverlayCanvas();
  });
}
function guestLogin() {
  fetch('/guest').then(function() {
    var ov = document.getElementById('login-overlay');
    if (ov) { ov.style.display='none'; ov.classList.add('hidden'); }
    var nm = document.getElementById('user-name');
    var wrap = document.getElementById('user-avatar-wrap');
    if (nm) nm.textContent = 'Guest';
    if (wrap) wrap.style.display = 'flex';
  }).catch(function() {
    var ov = document.getElementById('login-overlay');
    if (ov) { ov.style.display='none'; ov.classList.add('hidden'); }
  });
}
"""
html = re.sub(r'function initLoginOverlay\s*\(\s*\)\s*\{.*?(?=\nfunction )', clean_login_js + '\n', html, count=1, flags=re.DOTALL)
if 'function initLoginOverlay' not in html:
    idx = html.rfind("</script>")
    if idx != -1:
        html = html[:idx] + clean_login_js + html[idx:]
changes.append("FIX 6: initLoginOverlay rewritten clean")

# ============================================================
# FIX 7 - DOMContentLoaded: call initLoginOverlay + loadUserInfo
# ============================================================
new_dcl = """
document.addEventListener('DOMContentLoaded', function() {
  initLoginOverlay();
  loadUserInfo();
  filterEmptyDefaultFolders();
});
"""
# Remove existing DOMContentLoaded for these functions
html = re.sub(r'document\.addEventListener\s*\(\s*[\'"]DOMContentLoaded[\'"].*?initLoginOverlay.*?\}\s*\)\s*;', '', html, flags=re.DOTALL)
if 'initLoginOverlay' not in html.split('function initLoginOverlay')[0].split('DOMContentLoaded')[-1]:
    idx = html.rfind("</script>")
    if idx != -1:
        html = html[:idx] + new_dcl + html[idx:]
changes.append("FIX 7: DOMContentLoaded calls login + user info + folder filter")

# ============================================================
# FIX 8 - Remove Force show login overlay snippet if exists
# (it was conflicting with the proper version)
# ============================================================
html = html.replace("// Force show login overlay on every page load\n(function(){\n  var ov = document.getElementById('login-overlay');\n  if (ov) {\n    ov.style.display = 'flex';\n    ov.classList.remove('hidden');\n  }\n})();\n", "")
changes.append("FIX 8: Removed conflicting force-show snippet")

# ============================================================
# WRITE
# ============================================================
if html != original:
    with open(FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print("\nDone! " + str(len(changes)) + " fixes applied:")
    for c in changes:
        print("  + " + c)
    print("\nNow run:")
    print("  git add .")
    print('  git commit -m "Final UI fixes - toggles, login overlay, user info"')
    print("  git push origin main")
else:
    print("\nNo changes - check warnings above")
