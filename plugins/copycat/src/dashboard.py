"""Copycat Dashboard — template inventory viewer.

Generates a self-contained HTML file with embedded CSS, JS, and JSON data.
Dark theme with teal accent. Sidebar lists templates with search/filter.
Main content renders selected template's SKILL.md with placeholder highlighting.
"""

import json
import os
import webbrowser
from pathlib import Path

from src.shared import copycat_dir, templates_dir, now_iso
from src.registry import list_entries


def _read_template_content(template_id: str) -> str:
    """Read SKILL.md for a given template ID."""
    import re
    if not template_id or not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$", template_id):
        return ""
    path = templates_dir() / template_id / "SKILL.md"
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            pass
    return ""


def _collect_data() -> dict:
    """Build the data payload for the dashboard."""
    entries = list_entries()
    templates = []
    for entry in entries:
        tid = entry.get("id", "")
        content = _read_template_content(tid)
        templates.append({
            "id": tid,
            "name": entry.get("name", tid),
            "source_skill": entry.get("source_skill", ""),
            "source_project": entry.get("source_project", ""),
            "mode": entry.get("mode", ""),
            "placeholders": entry.get("placeholders", []),
            "placeholder_count": entry.get("placeholder_count", 0),
            "created": entry.get("created", ""),
            "updated": entry.get("updated", ""),
            "content": content,
        })
    return {
        "generated": now_iso(),
        "templates": templates,
    }


_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Copycat Dashboard</title>
<style>
:root {
  --bg: #121212; --bg2: #1e1e1e; --bg3: #2a2a2a;
  --fg: #e0e0e0; --fg2: #a0a0a0; --fg3: #6a6a6a;
  --accent: #00BCD4; --accent2: #00ACC1; --accent-dark: #b2ebf2;
  --border: #333333; --card-shadow: 0 2px 8px rgba(0,0,0,0.4);
  --code-bg: #252525; --tag-bg: #1a3a3f; --tag-fg: #00BCD4;
  --placeholder-bg: rgba(0,188,212,0.18); --placeholder-border: rgba(0,188,212,0.4);
  --sidebar-w: 300px;
  --radius: 12px;
}

* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif; background: var(--bg); color: var(--fg); display: flex; height: 100vh; overflow: hidden; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

/* Loading screen */
#loading {
  position: fixed; inset: 0; background: var(--bg); z-index: 999;
  display: flex; align-items: center; justify-content: center; flex-direction: column;
}
#loading .brand { font-size: 22px; font-weight: 700; margin-bottom: 6px; }
#loading .brand .slash { color: #4CAF50; }
#loading .brand .name { background: linear-gradient(135deg, #b0b8c1, #e0e4e8, #8a929a); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
#loading .subtitle { font-size: 13px; color: var(--fg3); margin-bottom: 22px; }
.progress-track { width: 220px; height: 3px; background: var(--border); border-radius: 2px; overflow: hidden; }
.progress-bar { width: 40%; height: 100%; background: var(--accent); border-radius: 2px; animation: loadSlide 1.2s ease-in-out infinite; }
@keyframes loadSlide { 0% { transform: translateX(-100%); } 100% { transform: translateX(350%); } }

/* Sidebar */
.sidebar { width: var(--sidebar-w); background: var(--bg2); border-right: 1px solid var(--border); display: flex; flex-direction: column; flex-shrink: 0; }
.sidebar-header { padding: 20px; border-bottom: 1px solid var(--border); }
.sidebar-brand { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.sidebar-brand h2 { font-size: 18px; font-weight: 700; letter-spacing: -0.3px; }
.sidebar-brand h2 .slash { color: #4CAF50; }
.sidebar-brand h2 .name { background: linear-gradient(135deg, #b0b8c1, #e0e4e8, #8a929a); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.sidebar-count { font-size: 12px; color: var(--fg3); }
.search-box { width: 100%; padding: 10px 14px; border: 1px solid var(--border); border-radius: 10px; background: var(--bg); color: var(--fg); font-size: 13px; outline: none; margin-top: 12px; transition: border 0.2s; }
.search-box:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(0,188,212,0.15); }
.template-list { flex: 1; overflow-y: auto; padding: 8px; }
.template-list.dragging { user-select: none; }
.template-item { padding: 12px 14px; border-radius: 10px; cursor: pointer; margin-bottom: 4px; transition: all 0.15s; }
.template-item:hover { background: var(--bg3); }
.template-item.active { background: var(--accent); color: #fff; }
.template-item-name { font-weight: 600; font-size: 14px; margin-bottom: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.template-item-meta { display: flex; align-items: center; gap: 8px; font-size: 11px; color: var(--fg3); }
.template-item.active .template-item-meta { color: rgba(255,255,255,0.7); }
.mode-badge { font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 8px; text-transform: uppercase; letter-spacing: 0.5px; }
.mode-badge.questionnaire { background: rgba(156,39,176,0.2); color: #CE93D8; border: 1px solid rgba(156,39,176,0.3); }
.mode-badge.sanitize { background: rgba(255,152,0,0.2); color: #FFB74D; border: 1px solid rgba(255,152,0,0.3); }
.mode-badge.unknown { background: rgba(100,100,100,0.2); color: #999; border: 1px solid rgba(100,100,100,0.3); }
.template-item.active .mode-badge { border-color: rgba(255,255,255,0.3); }
.template-item.active .mode-badge.questionnaire { background: rgba(255,255,255,0.15); color: #fff; }
.template-item.active .mode-badge.sanitize { background: rgba(255,255,255,0.15); color: #fff; }
.sidebar-footer { padding: 12px 16px; font-size: 11px; color: var(--fg3); border-top: 1px solid var(--border); }

/* Main */
.main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.topbar { padding: 14px 24px; border-bottom: 1px solid var(--border); background: var(--bg2); display: flex; align-items: center; gap: 14px; }
.topbar-title { font-size: 15px; font-weight: 600; color: var(--fg2); }
.topbar-title span { color: var(--accent); }
.content { flex: 1; overflow-y: auto; padding: 24px; }
.content.dragging { user-select: none; }
.empty { text-align: center; padding: 80px 20px; color: var(--fg3); }
.empty h3 { font-size: 18px; margin-bottom: 8px; color: var(--fg2); }

/* Detail panel */
.detail-panel { display: flex; gap: 24px; }
.detail-main { flex: 1; min-width: 0; }
.detail-sidebar { width: 280px; flex-shrink: 0; }

.detail-header { margin-bottom: 20px; }
.detail-header h1 { font-size: 22px; font-weight: 700; color: var(--accent-dark); margin-bottom: 6px; }
.detail-header .detail-id { font-size: 12px; color: var(--fg3); font-family: 'Cascadia Code', 'SF Mono', Consolas, monospace; }

.info-card { background: var(--bg2); border: 1px solid var(--border); border-radius: var(--radius); padding: 18px; margin-bottom: 14px; box-shadow: var(--card-shadow); }
.info-card h3 { font-size: 13px; font-weight: 600; color: var(--accent); text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 12px; }
.info-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 13px; }
.info-row:last-child { border-bottom: none; }
.info-label { color: var(--fg3); }
.info-value { color: var(--fg); font-weight: 500; }

.placeholder-list { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.placeholder-chip { font-size: 12px; font-family: 'Cascadia Code', 'SF Mono', Consolas, monospace; padding: 4px 10px; border-radius: 6px; background: var(--placeholder-bg); color: var(--accent); border: 1px solid var(--placeholder-border); }

.content-card { background: var(--bg2); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--card-shadow); overflow: hidden; }
.content-card-header { padding: 14px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
.content-card-header h3 { font-size: 14px; font-weight: 600; color: var(--accent-dark); }
.content-card-body { padding: 20px; }

.btn { padding: 7px 16px; border-radius: 8px; border: 1px solid var(--border); background: var(--bg2); color: var(--fg); cursor: pointer; font-size: 13px; font-weight: 500; transition: all 0.15s; }
.btn:hover { background: var(--bg3); border-color: var(--accent); }

/* Markdown */
.md-content h1 { font-size: 22px; font-weight: 700; color: var(--accent-dark); margin: 20px 0 10px; border-bottom: 2px solid var(--border); padding-bottom: 8px; }
.md-content h2 { font-size: 18px; font-weight: 600; color: var(--accent-dark); margin: 18px 0 8px; }
.md-content h3 { font-size: 15px; font-weight: 600; color: var(--fg); margin: 14px 0 6px; }
.md-content p { margin: 10px 0; line-height: 1.7; color: var(--fg2); }
.md-content ul, .md-content ol { margin: 10px 0 10px 24px; color: var(--fg2); }
.md-content li { margin: 5px 0; line-height: 1.6; }
.md-content code { background: var(--code-bg); padding: 2px 7px; border-radius: 5px; font-size: 13px; font-family: 'Cascadia Code', 'SF Mono', Consolas, monospace; color: var(--accent-dark); }
.md-content pre { background: var(--code-bg); padding: 16px; border-radius: 10px; overflow-x: auto; margin: 12px 0; border: 1px solid var(--border); }
.md-content pre code { background: none; padding: 0; color: var(--fg); }
.md-content a { color: var(--accent); }
.md-content strong { font-weight: 600; color: var(--fg); }
.md-content em { font-style: italic; }
.md-content hr { border: none; border-top: 1px solid var(--border); margin: 20px 0; }

/* Placeholder highlight in rendered markdown */
.ph-highlight { background: var(--placeholder-bg); border: 1px solid var(--placeholder-border); border-radius: 4px; padding: 1px 6px; font-family: 'Cascadia Code', 'SF Mono', Consolas, monospace; font-size: 12px; color: var(--accent); font-weight: 600; }

/* Hamburger (responsive) */
.hamburger { display: none; background: none; border: 1px solid var(--border); border-radius: 8px; width: 36px; height: 36px; cursor: pointer; color: var(--fg); font-size: 20px; align-items: center; justify-content: center; flex-shrink: 0; }
.sidebar-overlay { display: none; }

/* Responsive */
@media (max-width: 900px) {
  .detail-panel { flex-direction: column-reverse; }
  .detail-sidebar { width: 100%; }
}
@media (max-width: 640px) {
  body { flex-direction: column; }
  .hamburger { display: flex; }
  .sidebar { position: fixed; top: 0; left: -100%; width: 85%; max-width: 340px; height: 100vh; z-index: 200; border-right: 1px solid var(--border); transition: left 0.25s ease; box-shadow: none; }
  .sidebar.mobile-open { left: 0; box-shadow: 4px 0 24px rgba(0,0,0,0.4); }
  .sidebar-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 199; }
  .sidebar-overlay.visible { display: block; }
  .content { padding: 16px; }
  .topbar { gap: 8px; padding: 10px 14px; }
  .detail-panel { flex-direction: column-reverse; }
  .detail-sidebar { width: 100%; }
}
</style>
</head>
<body>
<div id="loading">
  <div class="brand"><span class="slash">/</span><span class="name">copycat</span></div>
  <div class="subtitle">Loading template inventory...</div>
  <div class="progress-track"><div class="progress-bar"></div></div>
</div>
<div class="sidebar">
  <div class="sidebar-header">
    <div class="sidebar-brand">
      <h2><span class="slash">/</span><span class="name">copycat</span></h2>
    </div>
    <div class="sidebar-count" id="templateCount"></div>
    <input class="search-box" id="search" type="text" placeholder="Search by name or source skill...">
  </div>
  <div class="template-list" id="templateList"></div>
  <div class="sidebar-footer" id="generated"></div>
</div>
<div class="main">
  <div class="sidebar-overlay" id="sidebarOverlay" onclick="closeMobileMenu()"></div>
  <div class="topbar">
    <button class="hamburger" onclick="toggleMobileMenu()" title="Templates">&#9776;</button>
    <div class="topbar-title"><span class="slash">/</span><span class="name">copycat</span> &mdash; Template Inventory</div>
  </div>
  <div class="content" id="content"></div>
</div>
<script>
const DATA = __DATA__;

let selectedId = null;
let searchQuery = '';

function init() {
  document.getElementById('generated').textContent = 'Generated: ' + new Date(DATA.generated).toLocaleString('en-GB', {day:'numeric',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'});
  updateCount();
  renderList();
  renderContent();
  document.getElementById('search').addEventListener('input', function(e) {
    searchQuery = e.target.value.toLowerCase();
    renderList();
    renderContent();
  });
}

function updateCount() {
  var total = DATA.templates.length;
  document.getElementById('templateCount').textContent = total + ' template' + (total !== 1 ? 's' : '') + ' in inventory';
}

function getFiltered() {
  var templates = DATA.templates;
  if (searchQuery) {
    templates = templates.filter(function(t) {
      return t.name.toLowerCase().indexOf(searchQuery) !== -1 ||
             t.source_skill.toLowerCase().indexOf(searchQuery) !== -1 ||
             t.id.toLowerCase().indexOf(searchQuery) !== -1;
    });
  }
  return templates;
}

function modeClass(mode) {
  if (mode === 'questionnaire') return 'questionnaire';
  if (mode === 'sanitize') return 'sanitize';
  return 'unknown';
}

function renderList() {
  var el = document.getElementById('templateList');
  var templates = getFiltered();
  if (!templates.length) {
    el.innerHTML = '<div style="padding:20px;text-align:center;color:var(--fg3);font-size:13px;">No templates match your search.</div>';
    return;
  }
  var html = '';
  for (var i = 0; i < templates.length; i++) {
    var t = templates[i];
    var active = selectedId === t.id ? 'active' : '';
    html += '<div class="template-item ' + active + '" onclick="selectTemplate(\'' + esc(t.id) + '\')">' +
      '<div class="template-item-name">' + esc(t.name) + '</div>' +
      '<div class="template-item-meta">' +
        '<span class="mode-badge ' + modeClass(t.mode) + '">' + esc(t.mode || '?') + '</span>' +
        '<span>' + t.placeholder_count + ' placeholder' + (t.placeholder_count !== 1 ? 's' : '') + '</span>' +
        (t.source_skill ? '<span>' + esc(t.source_skill) + '</span>' : '') +
      '</div>' +
    '</div>';
  }
  el.innerHTML = html;
}

function selectTemplate(id) {
  selectedId = id;
  closeMobileMenu();
  renderList();
  renderContent();
}

function renderContent() {
  var el = document.getElementById('content');
  if (!selectedId) {
    var filtered = getFiltered();
    if (!filtered.length) {
      el.innerHTML = '<div class="empty"><h3>No templates found</h3><p>Templates will appear here after you create them with /copycat.</p></div>';
    } else {
      el.innerHTML = '<div class="empty"><h3>Select a template</h3><p>Choose a template from the sidebar to view its content and details.</p></div>';
    }
    return;
  }
  var t = null;
  for (var i = 0; i < DATA.templates.length; i++) {
    if (DATA.templates[i].id === selectedId) { t = DATA.templates[i]; break; }
  }
  if (!t) {
    el.innerHTML = '<div class="empty"><h3>Template not found</h3></div>';
    return;
  }

  var phChips = '';
  if (t.placeholders && t.placeholders.length) {
    phChips = '<div class="placeholder-list">';
    for (var p = 0; p < t.placeholders.length; p++) {
      phChips += '<span class="placeholder-chip">{{' + esc(t.placeholders[p]) + '}}</span>';
    }
    phChips += '</div>';
  }

  var html = '<div class="detail-panel">' +
    '<div class="detail-main">' +
      '<div class="detail-header">' +
        '<h1>' + esc(t.name) + '</h1>' +
        '<div class="detail-id">' + esc(t.id) + '</div>' +
      '</div>' +
      '<div class="content-card">' +
        '<div class="content-card-header">' +
          '<h3>SKILL.md</h3>' +
          '<button class="btn" onclick="copyContent(this)">Copy content</button>' +
        '</div>' +
        '<div class="content-card-body md-content">' +
          (t.content ? renderMd(t.content) : '<p style="color:var(--fg3)">No SKILL.md content available.</p>') +
        '</div>' +
      '</div>' +
    '</div>' +
    '<div class="detail-sidebar">' +
      '<div class="info-card">' +
        '<h3>Details</h3>' +
        '<div class="info-row"><span class="info-label">Source Skill</span><span class="info-value">' + esc(t.source_skill || '—') + '</span></div>' +
        '<div class="info-row"><span class="info-label">Source Project</span><span class="info-value">' + esc(t.source_project || '—') + '</span></div>' +
        '<div class="info-row"><span class="info-label">Mode</span><span class="info-value"><span class="mode-badge ' + modeClass(t.mode) + '">' + esc(t.mode || '?') + '</span></span></div>' +
        '<div class="info-row"><span class="info-label">Created</span><span class="info-value">' + fmtDate(t.created) + '</span></div>' +
        '<div class="info-row"><span class="info-label">Updated</span><span class="info-value">' + fmtDate(t.updated) + '</span></div>' +
      '</div>' +
      '<div class="info-card">' +
        '<h3>Placeholders (' + t.placeholder_count + ')</h3>' +
        (phChips || '<div style="font-size:13px;color:var(--fg3);padding:4px 0;">No placeholders defined.</div>') +
      '</div>' +
    '</div>' +
  '</div>';

  el.innerHTML = html;
}

function copyContent(btn) {
  if (!selectedId) return;
  var t = null;
  for (var i = 0; i < DATA.templates.length; i++) {
    if (DATA.templates[i].id === selectedId) { t = DATA.templates[i]; break; }
  }
  if (!t || !t.content) return;
  navigator.clipboard.writeText(t.content).then(function() {
    var orig = btn.textContent;
    btn.textContent = 'Copied!';
    setTimeout(function() { btn.textContent = orig; }, 1000);
  });
}

function toggleMobileMenu() {
  document.querySelector('.sidebar').classList.toggle('mobile-open');
  document.getElementById('sidebarOverlay').classList.toggle('visible');
}

function closeMobileMenu() {
  document.querySelector('.sidebar').classList.remove('mobile-open');
  document.getElementById('sidebarOverlay').classList.remove('visible');
}

// --- Markdown renderer (no deps) ---
function renderMd(text) {
  if (!text) return '';
  var lines = text.split('\n');
  var html = '', inCode = false, codeBuf = [], inList = false, listType = '';

  function flushList() {
    if (inList) { html += listType === 'ol' ? '</ol>' : '</ul>'; inList = false; }
  }

  for (var i = 0; i < lines.length; i++) {
    var line = lines[i];
    if (line.indexOf('```') === 0) {
      if (inCode) { html += '<pre><code>' + esc(codeBuf.join('\n')) + '</code></pre>'; codeBuf = []; inCode = false; }
      else { flushList(); inCode = true; }
      continue;
    }
    if (inCode) { codeBuf.push(line); continue; }
    if (line === '---' && i < 3) continue;
    if (/^#{1,6}\s/.test(line)) {
      flushList();
      var lvl = line.match(/^(#+)/)[1].length;
      html += '<h' + lvl + '>' + inlineMd(line.replace(/^#+\s*/, '')) + '</h' + lvl + '>';
      continue;
    }
    if (/^[\-\*]\s/.test(line)) {
      if (!inList || listType !== 'ul') { flushList(); html += '<ul>'; inList = true; listType = 'ul'; }
      html += '<li>' + inlineMd(line.replace(/^[\-\*]\s*/, '')) + '</li>';
      continue;
    }
    if (/^\d+\.\s/.test(line)) {
      if (!inList || listType !== 'ol') { flushList(); html += '<ol>'; inList = true; listType = 'ol'; }
      html += '<li>' + inlineMd(line.replace(/^\d+\.\s*/, '')) + '</li>';
      continue;
    }
    flushList();
    if (line.trim() === '') continue;
    if (i < 5 && /^[a-z_]+:/.test(line)) continue;
    html += '<p>' + inlineMd(line) + '</p>';
  }
  flushList();
  if (inCode) html += '<pre><code>' + esc(codeBuf.join('\n')) + '</code></pre>';
  return html;
}

function inlineMd(text) {
  var result = esc(text)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, function(m, label, url) {
      if (/^(javascript|data|vbscript):/i.test(url)) return label;
      return '<a href="' + url + '" target="_blank">' + label + '</a>';
    });
  // Highlight {{placeholder}} patterns
  result = result.replace(/\{\{([^}]+)\}\}/g, '<span class="ph-highlight">{{$1}}</span>');
  return result;
}

function esc(s) {
  if (typeof s !== 'string') return '';
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function fmtDate(s) {
  if (!s) return '—';
  try { return new Date(s).toLocaleDateString('en-GB', {day:'numeric',month:'short',year:'numeric'}); }
  catch(e) { return s; }
}

document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape' && selectedId) { selectedId = null; renderList(); renderContent(); }
});

function enableDragScroll(el) {
  var isDown = false, startY, scrollTop;
  el.addEventListener('mousedown', function(e) {
    if (e.target.closest('button, a, input, select')) return;
    isDown = true; el.classList.add('dragging');
    startY = e.pageY - el.offsetTop; scrollTop = el.scrollTop;
  });
  el.addEventListener('mouseleave', function() { isDown = false; el.classList.remove('dragging'); });
  el.addEventListener('mouseup', function() { isDown = false; el.classList.remove('dragging'); });
  el.addEventListener('mousemove', function(e) {
    if (!isDown) return; e.preventDefault();
    el.scrollTop = scrollTop - (e.pageY - el.offsetTop - startY);
  });
}
document.querySelectorAll('.template-list, .content').forEach(enableDragScroll);

init();
document.getElementById('loading').style.display = 'none';
</script>
</body>
</html>"""


def generate(no_open: bool = False) -> dict:
    """Generate the dashboard HTML and optionally open it in the browser."""
    data = _collect_data()
    data_json = json.dumps(data, ensure_ascii=False)
    html = _HTML_TEMPLATE.replace("__DATA__", data_json)

    out_dir = copycat_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "dashboard.html"
    tmp_path = out_path.with_suffix(".tmp")
    tmp_path.write_text(html, encoding="utf-8")
    os.replace(str(tmp_path), str(out_path))

    if not no_open:
        webbrowser.open(out_path.as_uri())

    return {
        "status": "ok",
        "action": "dashboard_generated",
        "path": str(out_path),
        "ts": data["generated"],
        "templates": len(data["templates"]),
    }
