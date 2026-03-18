import re

FILE = "static/index.html"
print("Reading " + FILE + "...")
with open(FILE, "r", encoding="utf-8") as f:
    html = f.read()

original = html
changes = []

# ============================================================
# FIX 1 - Rewrite toggleSection to use inline styles (reliable)
# ============================================================
old_ts = "function toggleSection(b,a){var el=document.getElementById(b);var ar=document.getElementById(a);if(!el)return;el.classList.toggle('collapsed');if(ar)ar.classList.toggle('arrow-up');}"
new_ts = """function toggleSection(bodyId, arrowId) {
  var el = document.getElementById(bodyId);
  var ar = document.getElementById(arrowId);
  if (!el) return;
  if (el.style.maxHeight && el.style.maxHeight !== '0px') {
    el.style.maxHeight = '0px';
    el.style.overflow = 'hidden';
    if (ar) ar.style.transform = 'rotate(-90deg)';
  } else {
    el.style.maxHeight = el.scrollHeight + 200 + 'px';
    el.style.overflow = 'visible';
    if (ar) ar.style.transform = 'rotate(0deg)';
  }
}"""
if old_ts in html:
    html = html.replace(old_ts, new_ts, 1)
    changes.append("FIX 1: toggleSection rewritten with inline styles")
else:
    # try alternate form
    html2 = re.sub(
        r'function toggleSection\([^)]+\)\s*\{[^}]+\}',
        new_ts, html, count=1)
    if html2 != html:
        html = html2
        changes.append("FIX 1: toggleSection replaced (regex)")
    else:
        # just inject it fresh
        idx = html.rfind("</script>")
        if idx != -1:
            html = html[:idx] + "\n" + new_ts + "\n" + html[idx:]
            changes.append("FIX 1: toggleSection injected fresh")

# ============================================================
# FIX 2 - Add Style section toggle
# ============================================================
old_style = '<div class="f-lbl"><div class="f-dot amber"></div>Style</div>\n              <div class="style-grid">'
new_style = ('<div class="f-lbl" onclick="toggleSection(\'style-body\',\'style-arrow\')" '
             'style="cursor:pointer;display:flex;align-items:center;justify-content:space-between;user-select:none">'
             '<span style="display:flex;align-items:center;gap:6px"><div class="f-dot amber"></div>Style</span>'
             '<span id="style-arrow" style="font-size:9px;color:var(--tara-amber);transition:transform 0.2s">&#9660;</span>'
             '</div>\n'
             '<div id="style-body" style="max-height:200px;overflow:hidden;transition:max-height 0.3s ease">'
             '\n              <div class="style-grid">')
if old_style in html:
    # also close it
    old_style_end = '</div>\n            </div>\n\n            <div class="f-wrap">\n              <div class="complexity-row">'
    new_style_end = '</div>\n</div><!-- end style-body -->\n            </div>\n\n            <div class="f-wrap">\n              <div class="complexity-row">'
    html = html.replace(old_style, new_style, 1)
    if old_style_end in html:
        html = html.replace(old_style_end, new_style_end, 1)
    changes.append("FIX 2: Style section toggle added")
else:
    print("  WARN FIX2: Style section not found")

# ============================================================
# FIX 3 - Fix login overlay: always show, hide only if logged in
# Replace initLoginOverlay with smarter version
# ============================================================
old_init = "function initLoginOverlay() {\n  fetch('/auth/me').then(function(r){return r.json();}).then(function(d){\n    var ov = document.getElementById('login-overlay');\n    if (!ov) return;\n    if (d.logged_in) {\n      ov.classList.add('hidden');"
new_init = "function initLoginOverlay() {\n  // Always show overlay first, then hide if logged in\n  var ov = document.getElementById('login-overlay');\n  if (ov) ov.classList.remove('hidden');\n  fetch('/auth/me').then(function(r){return r.json();}).then(function(d){\n    if (!ov) return;\n    if (d.logged_in && d.user && d.user.sub !== 'anonymous') {\n      ov.classList.add('hidden');"
if old_init in html:
    html = html.replace(old_init, new_init, 1)
    changes.append("FIX 3: Login overlay always shows first, then hides if logged in")
else:
    print("  WARN FIX3: initLoginOverlay pattern not found")

# ============================================================
# FIX 4 - Fix user info display - also show email
# ============================================================
old_user_js = "function loadUserInfo(){fetch('/auth/me').then(function(r){return r.json();}).then(function(d){if(d.logged_in&&d.user){var w=document.getElementById('user-avatar-wrap');var img=document.getElementById('user-avatar');var nm=document.getElementById('user-name');if(w)w.style.display='flex';if(img&&d.user.picture)img.src=d.user.picture;if(nm&&d.user.name)nm.textContent=d.user.name;}}).catch(function(){});}"
new_user_js = """function loadUserInfo(){
  fetch('/auth/me').then(function(r){return r.json();}).then(function(d){
    if(d.logged_in && d.user){
      var w=document.getElementById('user-avatar-wrap');
      var img=document.getElementById('user-avatar');
      var nm=document.getElementById('user-name');
      if(w) w.style.display='flex';
      if(img && d.user.picture) img.src=d.user.picture;
      if(nm) {
        if(d.user.name && d.user.name !== 'Guest') {
          nm.textContent = d.user.name;
          nm.title = d.user.email || '';
        } else {
          nm.textContent = 'Guest';
        }
      }
    }
  }).catch(function(){});
}"""
if old_user_js in html:
    html = html.replace(old_user_js, new_user_js, 1)
    changes.append("FIX 4: loadUserInfo improved with email tooltip")
else:
    print("  WARN FIX4: loadUserInfo not found (may already be updated)")

# ============================================================
# FIX 5 - Remove default folders from left panel (show empty)
# The folders come from server DEFAULT_FOLDERS - fix folders display
# to only show user-created ones on first load
# Add a note in the UI via JS
# ============================================================
fix5_js = """
// Remove default empty folders from display if user hasn't used them
function filterEmptyDefaultFolders() {
  var defaults = ['vehicles','creatures','buildings','misc','bingoo','unchained'];
  setTimeout(function() {
    var items = document.querySelectorAll('.folder-row');
    items.forEach(function(item) {
      var nameEl = item.querySelector('.folder-name-txt');
      if (!nameEl) return;
      var name = nameEl.textContent.trim().toLowerCase();
      var countEl = item.querySelector('.folder-count');
      var count = countEl ? parseInt(countEl.textContent) : 0;
      if (defaults.indexOf(name) !== -1 && count === 0) {
        item.style.display = 'none';
      }
    });
  }, 1500);
}
document.addEventListener('DOMContentLoaded', filterEmptyDefaultFolders);
"""
if "filterEmptyDefaultFolders" not in html:
    idx = html.rfind("</script>")
    if idx != -1:
        html = html[:idx] + fix5_js + html[idx:]
        changes.append("FIX 5: Empty default folders hidden from UI")

# ============================================================
# FIX 6 - Add logout button to topbar user wrap
# ============================================================
old_userwrap = ('<div id="user-avatar-wrap" style="display:none;align-items:center;gap:8px;cursor:pointer" '
                'onclick="window.location=\'/auth/logout\'" title="Logout">')
new_userwrap = ('<div id="user-avatar-wrap" style="display:none;align-items:center;gap:8px;cursor:pointer" '
                'title="Click to logout" onclick="if(confirm(\'Logout?\')) window.location=\'/auth/logout\'">')
if old_userwrap in html:
    html = html.replace(old_userwrap, new_userwrap, 1)
    changes.append("FIX 6: Logout confirmation added")

# ============================================================
# WRITE
# ============================================================
if html != original:
    with open(FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print("\nDone! " + str(len(changes)) + " fixes applied:")
    for c in changes:
        print("  + " + c)
    print("\nNow run: git add . && git commit -m fixes && git push origin main")
else:
    print("\nNo changes - check warnings above")
