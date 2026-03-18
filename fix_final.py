import re

FILE = "static/index.html"
with open(FILE, "r", encoding="utf-8") as f:
    html = f.read()

original = html
changes = []

# ============================================================
# FIX 1 — Remove orphan "} else {" block at line ~5416
# This is broken leftover code causing SyntaxError
# ============================================================
# Remove the orphan else block
html2 = re.sub(
    r'\n\s*\} else \{\s*\n\s*// Temporarily remove max-height.*?el\.style\.transition = \'max-height 0\.3s ease\';\s*\}\s*\n',
    '\n',
    html, flags=re.DOTALL, count=1
)
if html2 != html:
    html = html2
    changes.append("FIX 1: Removed orphan else block (SyntaxError)")
else:
    print("  WARN FIX1: orphan else not found - trying alt pattern")
    html2 = re.sub(
        r' else \{\s*\n\s*// Temporarily remove max-height to measure real scrollHeight\s*\n.*?el\.style\.transition = .max-height 0\.3s ease.;\s*\}\s*\n',
        '\n', html, flags=re.DOTALL, count=1)
    if html2 != html:
        html = html2
        changes.append("FIX 1b: Removed orphan else block (alt pattern)")

# ============================================================
# FIX 2 — Remove the broken toggleSection FRAGMENT (no function decl)
# Keep the real one below it
# ============================================================
# The broken fragment looks like: comment block then starts with "  var isOpen ="
# without a "function toggleSection" declaration
html2 = re.sub(
    r'/\* ={60,}\s*\n\s*TOGGLE SECTION.*?={60,} \*/\s*\n\s*\n\s*// Check current state via data attribute.*?if \(ar\) ar\.style\.transform = \'rotate\(0deg\)\';\s*\n\s*\}\s*\n\s*\}\s*\n',
    '\n',
    html, flags=re.DOTALL, count=1
)
if html2 != html:
    html = html2
    changes.append("FIX 2: Removed broken toggleSection fragment")
else:
    print("  WARN FIX2: trying exact fragment match")
    # Try to remove the specific orphan code
    frag = re.search(
        r'(\/\* ={20,}.*?TOGGLE SECTION.*?={20,} \*\/\s*\n)(.*?)(function toggleSection)',
        html, flags=re.DOTALL
    )
    if frag:
        # Check if the code between comment and function def is NOT "function toggleSection"
        between = frag.group(2)
        if 'function toggleSection' not in between and len(between) > 20:
            html = html[:frag.start(2)] + html[frag.start(3):]
            changes.append("FIX 2b: Removed broken fragment between comment and function")

# ============================================================
# FIX 3 — Remove duplicate DOMContentLoaded for toggle init
# Keep only ONE (the one that calls initLoginOverlay too)
# ============================================================
# Remove the extra DOMContentLoaded that ONLY does toggle init
html2 = re.sub(
    r'/\* Run on load to set correct initial arrow states \*/\s*\ndocument\.addEventListener\(\'DOMContentLoaded\', function\(\) \{\s*\n\s*\[\'shapes-body\'.*?fa\.style\.transform = \'rotate\(0deg\)\';\s*\n\s*\}\);\s*\n\s*\n\s*/\* Run on load to set correct initial arrow states \*/\s*\ndocument\.addEventListener\(\'DOMContentLoaded\', function\(\) \{\s*\n\s*\[\'shapes-body\'.*?fa\.style\.transform = \'rotate\(0deg\)\';\s*\n\s*\}\);',
    '/* Run on load to set correct initial arrow states */\ndocument.addEventListener(\'DOMContentLoaded\', function() {\n  [\'shapes-body\',\'color-body\',\'style-body\'].forEach(function(id) {\n    var el = document.getElementById(id);\n    if (el) { el.setAttribute(\'data-ts-open\', \'0\'); el.style.maxHeight = \'0px\'; el.style.overflow = \'hidden\'; }\n  });\n  [\'shapes-arrow\',\'color-arrow\',\'style-arrow\'].forEach(function(id) {\n    var el = document.getElementById(id);\n    if (el) el.style.transform = \'rotate(-90deg)\';\n  });\n  var fp = document.getElementById(\'folder-panel-body\');\n  if (fp) { fp.setAttribute(\'data-ts-open\', \'1\'); fp.style.overflow = \'hidden\'; }\n  var fa = document.getElementById(\'folder-panel-arrow\');\n  if (fa) fa.style.transform = \'rotate(0deg)\';\n});',
    html, flags=re.DOTALL, count=1
)
if html2 != html:
    html = html2
    changes.append("FIX 3: Removed duplicate DOMContentLoaded")

# ============================================================
# FIX 4 — Make cursor bigger and more visible
# ============================================================
html = html.replace(
    '#cursor-dot{\n  width:8px;height:8px;background:var(--gold);\n  box-shadow:0 0 8px var(--gold),0 0 16px rgba(255,215,0,.5);\n  transition:transform .08s ease,background .2s;\n}',
    '#cursor-dot{\n  width:12px;height:12px;background:var(--gold);\n  box-shadow:0 0 12px var(--gold),0 0 28px rgba(255,215,0,.7),0 0 50px rgba(255,215,0,.2);\n  transition:transform .08s ease,background .2s;\n}'
)
html = html.replace(
    '#cursor-ring{\n  width:32px;height:32px;\n  border:1px solid rgba(0,212,255,.5);\n  box-shadow:0 0 8px rgba(0,212,255,.2);\n  transition:width .15s,height .15s,border-color .15s;\n}',
    '#cursor-ring{\n  width:36px;height:36px;\n  border:1.5px solid rgba(0,212,255,.7);\n  box-shadow:0 0 12px rgba(0,212,255,.35),inset 0 0 8px rgba(0,212,255,.1);\n  transition:width .15s,height .15s,border-color .15s;\n}'
)
changes.append("FIX 4: Cursor made bigger and brighter")

# ============================================================
# FIX 5 — Fix filterEmptyDefaultFolders to also run after folders load
# The current 1500ms delay is not enough if folders load slowly
# ============================================================
old_filter = '''function filterEmptyDefaultFolders() {
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
}'''
new_filter = '''function filterEmptyDefaultFolders() {
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
if old_filter in html:
    html = html.replace(old_filter, new_filter, 1)
    changes.append("FIX 5: filterEmptyDefaultFolders runs at 800ms, 2000ms, 4000ms")

# ============================================================
# SAVE
# ============================================================
if html != original:
    with open(FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print("DONE! " + str(len(changes)) + " fixes applied:")
    for c in changes:
        print("  + " + c)
else:
    print("No changes - patterns not found, may already be fixed")
