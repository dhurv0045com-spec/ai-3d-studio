import re

# ============================================================
# FIX server.py — Make generation use OpenRouter/OpenAI fallback
# ============================================================
print("=== Fixing server.py ===")
with open("server.py", "r", encoding="utf-8") as f:
    srv = f.read()

srv_orig = srv

# Replace all call_llm( calls in generation with call_llm_unified(
# and handle the tuple return properly
lines = srv.split('\n')
new_lines = []
i = 0
replaced = 0
while i < len(lines):
    line = lines[i]
    # Match lines like: "    raw = call_llm(" or "    script_raw = call_llm("
    m = re.match(r'^(\s*)(\w+)\s*=\s*call_llm\(', line)
    if m and 'def call_llm' not in line and 'call_llm_unified' not in line:
        indent = m.group(1)
        varname = m.group(2)
        # Replace call_llm( with call_llm_unified(
        new_line = line.replace('= call_llm(', '= call_llm_unified(', 1)
        # Add unpacking line after
        new_lines.append(new_line)
        new_lines.append(indent + varname + '_provider = ' + varname + '[1] if isinstance(' + varname + ', tuple) else "Gemini"')
        new_lines.append(indent + varname + ' = ' + varname + '[0] if isinstance(' + varname + ', tuple) else ' + varname)
        replaced += 1
    else:
        new_lines.append(line)
    i += 1

srv = '\n'.join(new_lines)
if srv != srv_orig:
    with open("server.py", "w", encoding="utf-8") as f:
        f.write(srv)
    print(f"  + server.py: {replaced} call_llm() replaced with call_llm_unified()")
else:
    print("  INFO: server.py already updated or no changes needed")

# ============================================================
# FIX index.html
# ============================================================
print("\n=== Fixing index.html ===")
with open("static/index.html", "r", encoding="utf-8") as f:
    html = f.read()

html_orig = html
changes = []

# --- FIX 1: Remove broken orphan JS fragments ---
# Remove orphan "} else {" block
html2 = re.sub(
    r'\n else \{\s*\n\s*// Temporarily remove max-height to measure real scrollHeight\s*\n.*?el\.style\.transition = [\'"]max-height[^;]+;\s*\}\s*\n',
    '\n', html, flags=re.DOTALL, count=1)
if html2 != html:
    html = html2
    changes.append("FIX 1a: Removed orphan else block")

# Remove broken toggleSection fragment (no function declaration before it)
html2 = re.sub(
    r'(/\* ={15,}.*?TOGGLE SECTION.*?={15,} \*/\s*\n)\s*\n\s*// Check current state via data attribute.*?if \(ar\) ar\.style\.transform = \'rotate\(0deg\)\';\s*\n\s*\}\s*\n\s*\}\s*\n',
    '', html, flags=re.DOTALL, count=1)
if html2 != html:
    html = html2
    changes.append("FIX 1b: Removed broken toggleSection fragment")

# --- FIX 2: Remove ALL duplicate DOMContentLoaded toggle inits, keep one ---
# Find and remove extra DOMContentLoaded blocks that only do toggle init
toggle_dcl_pattern = r"/\* Run on load to set correct initial arrow states \*/\s*\ndocument\.addEventListener\('DOMContentLoaded',\s*function\(\)\s*\{.*?fa\.style\.transform\s*=\s*'rotate\(0deg\)';\s*\n\s*\}\);\s*\n"
matches = list(re.finditer(toggle_dcl_pattern, html, flags=re.DOTALL))
if len(matches) > 1:
    # Remove all but last
    for m in matches[:-1]:
        html = html.replace(m.group(0), '', 1)
    changes.append(f"FIX 2: Removed {len(matches)-1} duplicate DOMContentLoaded toggle inits")

# --- FIX 3: Cursor - make dot bigger and visible ---
html = html.replace(
    '#cursor-dot{\n  width:8px;height:8px;background:var(--gold);',
    '#cursor-dot{\n  width:14px;height:14px;background:var(--gold);'
)
html = html.replace(
    'box-shadow:0 0 8px var(--gold),0 0 16px rgba(255,215,0,.5);',
    'box-shadow:0 0 14px var(--gold),0 0 30px rgba(255,215,0,.6),0 0 60px rgba(255,215,0,.15);'
)
html = html.replace(
    'width:32px;height:32px;\n  border:1px solid rgba(0,212,255,.5);\n  box-shadow:0 0 8px rgba(0,212,255,.2);',
    'width:40px;height:40px;\n  border:1.5px solid rgba(0,212,255,.75);\n  box-shadow:0 0 16px rgba(0,212,255,.4),inset 0 0 8px rgba(0,212,255,.1);'
)
changes.append("FIX 3: Cursor made bigger and brighter")

# --- FIX 4: Hide empty state when model loads ---
# Find loadGLB function and ensure it hides empty state
old_es = "var es = document.getElementById('empty-state');\n    if (es) { es.style.display = 'none'; }"
if old_es not in html:
    html = html.replace(
        "function loadGLB(url, onLoad) {",
        "function loadGLB(url, onLoad) {\n  var es = document.getElementById('empty-state');\n  if (es) es.style.display = 'none';"
    , 1)
    changes.append("FIX 4: Empty state hides when model loads")

# --- FIX 5: folder-cnt-badge CSS (badge class name mismatch) ---
# The JS uses folder-cnt-badge but CSS has folder-count
if '.folder-cnt-badge' not in html:
    css_add = "\n.folder-cnt-badge{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--tx-4);background:var(--bg-3);padding:1px 5px;border-radius:8px;min-width:18px;text-align:center;}\n.folder-row.active .folder-cnt-badge{background:rgba(201,168,76,.15);color:var(--kuro-ochre);}\n"
    html = html.replace("</style>", css_add + "</style>", 1)
    changes.append("FIX 5: folder-cnt-badge CSS added")

# --- FIX 6: Filter empty default folders - run more often and check correct class ---
old_filter = '''function filterEmptyDefaultFolders() {
  var defaults = ['vehicles','creatures','buildings','misc','bingoo','unchained'];
  function doFilter() {
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
  }
  setTimeout(doFilter, 800);
  setTimeout(doFilter, 2000);
  setTimeout(doFilter, 4000);
}'''
new_filter = '''function filterEmptyDefaultFolders() {
  var defaults = ['vehicles','creatures','buildings','misc','bingoo','unchained'];
  function doFilter() {
    document.querySelectorAll('.folder-row').forEach(function(item) {
      var nameEl = item.querySelector('.folder-name-txt');
      if (!nameEl) return;
      var name = nameEl.textContent.trim().toLowerCase();
      // Check both possible badge class names
      var countEl = item.querySelector('.folder-count, .folder-cnt-badge');
      var count = countEl ? (parseInt(countEl.textContent) || 0) : 0;
      if (defaults.indexOf(name) !== -1 && count === 0) {
        item.style.display = 'none';
      } else {
        item.style.display = '';
      }
    });
  }
  [500, 1500, 3000, 6000].forEach(function(t){ setTimeout(doFilter, t); });
}'''
if old_filter in html:
    html = html.replace(old_filter, new_filter, 1)
    changes.append("FIX 6: filterEmptyDefaultFolders improved")
elif 'filterEmptyDefaultFolders' in html:
    # Try to patch whatever version exists
    html = re.sub(
        r"function filterEmptyDefaultFolders\(\).*?(?=\ndocument\.addEventListener\('DOMContentLoaded', filterEmpty|\nfunction |\n\/\* )",
        new_filter + '\n',
        html, flags=re.DOTALL, count=1)
    changes.append("FIX 6b: filterEmptyDefaultFolders replaced")

# --- FIX 7: Fix save - ensure showSaveModal works and folder-select is populated ---
# Check if folder-select gets populated in showSaveModal
if 'folder-select' in html and 'syncDropdowns' in html:
    # Make sure syncDropdowns is called on save modal open
    old_save = "function showSaveModal() {"
    new_save = "function showSaveModal() {\n  syncDropdowns();"
    if old_save in html and "function showSaveModal() {\n  syncDropdowns();" not in html:
        html = html.replace(old_save, new_save, 1)
        changes.append("FIX 7: syncDropdowns called on save modal open")

# --- FIX 8: Make empty state hide after generation ---
if "empty-state" in html:
    old_gen_done = "loadGLB('/rocket.glb?t=' + Date.now(), function() {"
    new_gen_done = "loadGLB('/rocket.glb?t=' + Date.now(), function() {\n          var _es = document.getElementById('empty-state'); if(_es) _es.style.display='none';"
    if old_gen_done in html and "_es = document.getElementById('empty-state')" not in html:
        html = html.replace(old_gen_done, new_gen_done, 1)
        changes.append("FIX 8: Empty state hidden after generation")

# --- FIX 9: loadUserInfo always shows avatar when logged in ---
old_lui = """function loadUserInfo() {
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
}"""
new_lui = """function loadUserInfo() {
  fetch('/auth/me').then(function(r) { return r.json(); }).then(function(d) {
    var wrap = document.getElementById('user-avatar-wrap');
    var img  = document.getElementById('user-avatar');
    var nm   = document.getElementById('user-name');
    var em   = document.getElementById('user-email');
    if (d.logged_in && d.user) {
      if (wrap) { wrap.style.display = 'flex'; }
      if (img) {
        if (d.user.picture) {
          img.src = d.user.picture;
          img.style.display = 'block';
        } else {
          img.style.display = 'none';
        }
      }
      if (nm) nm.textContent = d.user.name || (d.user.email ? d.user.email.split('@')[0] : 'User');
      if (em) em.textContent = d.user.email || '';
    }
  }).catch(function() {});
}"""
if old_lui in html:
    html = html.replace(old_lui, new_lui, 1)
    changes.append("FIX 9: loadUserInfo improved - shows name from email if no name")

# --- FIX 10: Add CSS for folders count badge fallback ---
if '.folder-count' not in html:
    pass  # already there

# SAVE
if html != html_orig:
    with open("static/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  DONE! {len(changes)} fixes applied:")
    for c in changes:
        print("  + " + c)
else:
    print("  No changes made")

print("\nNow run:")
print("  git add .")
print("  git commit -m 'Fix OpenRouter in pipeline + all UI bugs'")
print("  git push origin main")
print("\nAlso add to Railway Variables:")
print("  OPENROUTER_KEY_1 = your-openrouter-key")
print("  OPENROUTER_MODEL = meta-llama/llama-3.1-8b-instruct:free")
