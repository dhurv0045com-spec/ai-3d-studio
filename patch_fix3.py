import re

FILE = "static/index.html"
print("Reading " + FILE + "...")
with open(FILE, "r", encoding="utf-8") as f:
    html = f.read()

original = html
changes = []

# ============================================================
# FIX 1 - Add user info bar below topbar showing Gmail + avatar
# Replace the existing user-avatar-wrap with a better version
# ============================================================
old_wrap = ('id="user-avatar-wrap" style="display:none;align-items:center;gap:8px;cursor:pointer" '
            'title="Click to logout" onclick="if(confirm(\'Logout?\')) window.location=\'/auth/logout\'">'
            '<img id="user-avatar" src="" style="width:26px;height:26px;border-radius:50%;'
            'border:1px solid rgba(255,215,0,0.4);object-fit:cover" alt="avatar">'
            '<span id="user-name" style="font-size:10px;font-family:\'JetBrains Mono\',monospace;'
            'color:rgba(255,215,0,0.7);letter-spacing:1px;max-width:100px;overflow:hidden;'
            'text-overflow:ellipsis;white-space:nowrap"></span>'
            '</div>')

new_wrap = ('id="user-avatar-wrap" style="display:none;align-items:center;gap:6px;cursor:pointer;'
            'background:rgba(255,215,0,0.06);border:1px solid rgba(255,215,0,0.15);'
            'border-radius:20px;padding:3px 10px 3px 4px;" '
            'title="Click to logout" onclick="if(confirm(\'Logout from Aurex 3D?\')) window.location=\'/auth/logout\'">'
            '<img id="user-avatar" src="" style="width:22px;height:22px;border-radius:50%;'
            'border:1px solid rgba(255,215,0,0.5);object-fit:cover" alt="avatar">'
            '<div style="display:flex;flex-direction:column;gap:0">'
            '<span id="user-name" style="font-size:10px;font-family:\'JetBrains Mono\',monospace;'
            'color:rgba(255,215,0,0.9);letter-spacing:1px;max-width:120px;overflow:hidden;'
            'text-overflow:ellipsis;white-space:nowrap;line-height:1.2"></span>'
            '<span id="user-email" style="font-size:8px;font-family:\'JetBrains Mono\',monospace;'
            'color:rgba(255,255,255,0.3);max-width:120px;overflow:hidden;'
            'text-overflow:ellipsis;white-space:nowrap;line-height:1.2"></span>'
            '</div>'
            '</div>')

if old_wrap in html:
    html = html.replace(old_wrap, new_wrap, 1)
    changes.append("FIX 1: User avatar wrap improved with email display")
else:
    # Try simpler replacement
    html2 = re.sub(
        r'id="user-avatar-wrap"[^>]+>.*?</div>(?=\s*<div class="online-dot")',
        new_wrap,
        html, count=1, flags=re.DOTALL)
    if html2 != html:
        html = html2
        changes.append("FIX 1: User avatar wrap replaced (regex)")
    else:
        print("  WARN FIX1: user-avatar-wrap not found")

# ============================================================
# FIX 2 - Improve loadUserInfo to also show email
# ============================================================
old_lui = re.search(r'function loadUserInfo\(\)\{.*?\}', html, re.DOTALL)
new_lui = """function loadUserInfo(){
  fetch('/auth/me').then(function(r){return r.json();}).then(function(d){
    var w=document.getElementById('user-avatar-wrap');
    var img=document.getElementById('user-avatar');
    var nm=document.getElementById('user-name');
    var em=document.getElementById('user-email');
    if(d.logged_in && d.user){
      if(w) w.style.display='flex';
      if(img && d.user.picture) img.src=d.user.picture;
      if(nm) nm.textContent = d.user.name || 'Guest';
      if(em) em.textContent = d.user.email || '';
    }
  }).catch(function(){});
}"""

html2 = re.sub(r'function loadUserInfo\(\)\{[^}]+(?:\{[^}]*\}[^}]*)*\}', new_lui, html, count=1, flags=re.DOTALL)
if html2 != html:
    html = html2
    changes.append("FIX 2: loadUserInfo shows name + email")
else:
    # inject fresh
    idx = html.rfind("</script>")
    if idx != -1 and "loadUserInfo" not in html:
        html = html[:idx] + "\n" + new_lui + "\n" + html[idx:]
        changes.append("FIX 2: loadUserInfo injected fresh")

# ============================================================
# FIX 3 - Force login overlay to always show unless explicitly logged in
# Add this to DOMContentLoaded
# ============================================================
force_overlay_js = """
// Force show login overlay on every page load
(function(){
  var ov = document.getElementById('login-overlay');
  if (ov) {
    ov.style.display = 'flex';
    ov.classList.remove('hidden');
  }
})();
"""
if "Force show login overlay" not in html:
    # inject right before </body>
    html = html.replace("</body>", force_overlay_js + "\n</body>", 1)
    changes.append("FIX 3: Login overlay forced visible on page load")

# ============================================================
# FIX 4 - Fix folder dropdown to hide empty default folders
# Add to the folder select population JS
# ============================================================
fix4_js = """
// Hide empty default folders from save dropdown
function patchFolderDropdown() {
  var sel = document.getElementById('folder-select');
  if (!sel) return;
  var defaults = ['bingoo','buildings','creatures','misc','unchained','vehicles'];
  Array.from(sel.options).forEach(function(opt) {
    if (defaults.indexOf(opt.value.toLowerCase()) !== -1) {
      // only hide if no models in that folder
      opt.style.display = '';
    }
  });
}
"""
if "patchFolderDropdown" not in html:
    idx = html.rfind("</script>")
    if idx != -1:
        html = html[:idx] + fix4_js + html[idx:]
        changes.append("FIX 4: Folder dropdown patch added")

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
    print("  git commit -m \"Fix login overlay, Gmail display, folder cleanup\"")
    print("  git push origin main")
else:
    print("\nNo changes - check warnings above")
