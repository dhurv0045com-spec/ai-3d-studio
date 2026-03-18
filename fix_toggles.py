FILE = "static/index.html"
with open(FILE, "r", encoding="utf-8") as f:
    html = f.read()

# The nuclear fix for toggleSection — remove ALL existing versions and inject fresh
import re

# Remove all existing toggleSection definitions
html = re.sub(
    r'function toggleSection\s*\([^)]*\)\s*\{[^}]*(?:\{[^}]*\}[^}]*)*\}',
    '', html, flags=re.DOTALL
)

# Inject at top of last <script> block
NEW_TS = """
/* ================================================================
   TOGGLE SECTION — Rock solid implementation
   Uses actual height measurement, not scrollHeight (which fails on hidden elements)
   ================================================================ */
function toggleSection(bodyId, arrowId) {
  var el = document.getElementById(bodyId);
  var ar = document.getElementById(arrowId);
  if (!el) { console.warn('toggleSection: element not found:', bodyId); return; }

  // Check current state via data attribute (reliable, not affected by CSS)
  var isOpen = el.getAttribute('data-ts-open') === '1';

  if (isOpen) {
    // CLOSE: animate to 0
    el.style.maxHeight = el.scrollHeight + 'px'; // set current first
    el.offsetHeight; // force reflow
    el.style.transition = 'max-height 0.3s ease';
    el.style.maxHeight = '0px';
    el.style.overflow = 'hidden';
    el.setAttribute('data-ts-open', '0');
    if (ar) ar.style.transform = 'rotate(-90deg)';
  } else {
    // OPEN: measure real height by temporarily removing max-height
    el.style.transition = 'none';
    el.style.maxHeight = 'none';
    el.style.overflow = 'visible';
    var h = el.scrollHeight;
    el.style.maxHeight = '0px';
    el.style.overflow = 'hidden';
    el.offsetHeight; // force reflow
    el.style.transition = 'max-height 0.32s cubic-bezier(0.4,0,0.2,1)';
    el.style.maxHeight = (h + 20) + 'px';
    el.setAttribute('data-ts-open', '1');
    if (ar) ar.style.transform = 'rotate(0deg)';
  }
}

/* Run on load to set correct initial arrow states */
document.addEventListener('DOMContentLoaded', function() {
  ['shapes-body','color-body','style-body'].forEach(function(id) {
    var el = document.getElementById(id);
    if (el) {
      el.setAttribute('data-ts-open', '0');
      el.style.maxHeight = '0px';
      el.style.overflow = 'hidden';
    }
  });
  ['shapes-arrow','color-arrow','style-arrow'].forEach(function(id) {
    var el = document.getElementById(id);
    if (el) el.style.transform = 'rotate(-90deg)';
  });
  var fp = document.getElementById('folder-panel-body');
  if (fp) {
    fp.setAttribute('data-ts-open', '1');
    fp.style.overflow = 'hidden';
  }
  var fa = document.getElementById('folder-panel-arrow');
  if (fa) fa.style.transform = 'rotate(0deg)';
});
"""

# Find the last </script> and inject before it
idx = html.rfind("</script>")
if idx != -1:
    html = html[:idx] + NEW_TS + "\n" + html[idx:]
    print("toggleSection injected")
else:
    print("ERROR: No </script> found")

with open(FILE, "w", encoding="utf-8") as f:
    f.write(html)

print("Done. Run: git add . && git commit -m 'Fix toggles + new login page' && git push origin main")
