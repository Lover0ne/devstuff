"""Skilltrace Dashboard — generates a static HTML viewer for all projects and skills.

Scans home directory for .skilltrace markers, reads registry + skill files,
outputs a self-contained HTML file with embedded data and opens it in the browser.
"""

import json
import re
import webbrowser
from pathlib import Path

from src.shared import skilltrace_dir, now_iso, receipt
from src.registry import load_registry


_MAX_DEPTH = 6
_SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".tox", ".mypy_cache", ".pytest_cache", "dist", "build",
    ".next", ".nuxt", "target", "bin", "obj", ".cache",
    "AppData", "Application Data", ".npm", ".yarn",
}


def _find_projects() -> list[dict]:
    projects = []
    seen_ids = set()

    def _walk(directory: Path, depth: int):
        if depth > _MAX_DEPTH:
            return
        try:
            entries = sorted(directory.iterdir())
        except (PermissionError, OSError):
            return
        for entry in entries:
            if not entry.is_dir():
                if entry.name == ".skilltrace" and entry.is_file():
                    try:
                        data = json.loads(entry.read_text(encoding="utf-8"))
                        pid = data.get("project_id")
                        if pid and not data.get("declined") and pid not in seen_ids:
                            seen_ids.add(pid)
                            projects.append({
                                "id": pid,
                                "name": entry.parent.name,
                                "path": str(entry.parent),
                            })
                    except (json.JSONDecodeError, OSError):
                        pass
                continue
            if entry.name.startswith(".") and entry.name != ".claude":
                continue
            if entry.name in _SKIP_DIRS:
                continue
            _walk(entry, depth + 1)

    _walk(Path.home(), 0)
    return projects


def _read_skill_content(project_path: str, skill_id: str) -> str:
    p = Path(project_path) / ".claude" / "skills" / skill_id / "SKILL.md"
    if p.exists():
        try:
            return p.read_text(encoding="utf-8")
        except OSError:
            pass
    return ""


def _read_versions(project_path: str, skill_id: str, current_version: int) -> list[dict]:
    versions = []
    ver_base = Path(project_path) / ".claude" / "skilltrace" / "versions" / skill_id
    for v in range(1, current_version):
        vpath = ver_base / f"v{v}.md"
        if vpath.exists():
            try:
                versions.append({"version": v, "content": vpath.read_text(encoding="utf-8")})
            except OSError:
                pass
    current_content = _read_skill_content(project_path, skill_id)
    if current_content:
        versions.append({"version": current_version, "content": current_content, "current": True})
    return versions


def _collect_data() -> dict:
    projects = _find_projects()
    registry = load_registry()
    skills_by_project = {}
    for skill in registry.get("skills", []):
        pid = skill.get("project_id", "unknown")
        if pid not in skills_by_project:
            skills_by_project[pid] = []
        skills_by_project[pid].append(skill)

    result_projects = []
    for proj in projects:
        pid = proj["id"]
        proj_skills = skills_by_project.get(pid, [])
        enriched_skills = []
        for s in proj_skills:
            sid = s.get("id", "")
            ver = s.get("version", 1)
            enriched_skills.append({
                "id": sid,
                "name": s.get("name", sid),
                "description": s.get("description", ""),
                "tags": s.get("tags", []),
                "current_version": ver,
                "created": s.get("created", ""),
                "updated": s.get("updated", ""),
                "versions": _read_versions(proj["path"], sid, ver),
            })
        result_projects.append({
            "id": pid,
            "name": proj["name"],
            "path": proj["path"],
            "skills": enriched_skills,
        })

    return {
        "generated": now_iso(),
        "projects": result_projects,
    }


_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Skilltrace Dashboard</title>
<style>
:root {
  --bg: #f5f5f5; --bg2: #ffffff; --bg3: #e8e8e8;
  --fg: #1a1a1a; --fg2: #555; --fg3: #888;
  --accent: #2563eb; --accent2: #1d4ed8;
  --border: #ddd; --card-shadow: 0 1px 3px rgba(0,0,0,0.08);
  --diff-add: #d4edda; --diff-rm: #f8d7da;
  --diff-add-fg: #155724; --diff-rm-fg: #721c24;
  --code-bg: #f0f0f0; --tag-bg: #e0e7ff; --tag-fg: #3730a3;
  --sidebar-w: 260px;
}
[data-theme="dark"] {
  --bg: #0f0f0f; --bg2: #1a1a1a; --bg3: #2a2a2a;
  --fg: #e5e5e5; --fg2: #aaa; --fg3: #666;
  --accent: #60a5fa; --accent2: #93bbfc;
  --border: #333; --card-shadow: 0 1px 3px rgba(0,0,0,0.3);
  --diff-add: #1a3a2a; --diff-rm: #3a1a1a;
  --diff-add-fg: #6ee7b7; --diff-rm-fg: #fca5a5;
  --code-bg: #2d2d2d; --tag-bg: #1e1b4b; --tag-fg: #a5b4fc;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: var(--bg); color: var(--fg); display: flex; height: 100vh; overflow: hidden; }
.sidebar { width: var(--sidebar-w); background: var(--bg2); border-right: 1px solid var(--border); display: flex; flex-direction: column; flex-shrink: 0; }
.sidebar-header { padding: 16px; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; }
.sidebar-header h2 { font-size: 15px; font-weight: 600; }
.theme-btn { background: none; border: 1px solid var(--border); border-radius: 6px; padding: 4px 8px; cursor: pointer; color: var(--fg); font-size: 14px; }
.project-list { flex: 1; overflow-y: auto; padding: 8px; }
.project-item { padding: 10px 12px; border-radius: 8px; cursor: pointer; margin-bottom: 4px; display: flex; justify-content: space-between; align-items: center; font-size: 14px; }
.project-item:hover { background: var(--bg3); }
.project-item.active { background: var(--accent); color: white; }
.project-item .count { font-size: 12px; opacity: 0.7; background: var(--bg3); border-radius: 10px; padding: 2px 8px; }
.project-item.active .count { background: rgba(255,255,255,0.2); }
.main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.topbar { padding: 12px 20px; border-bottom: 1px solid var(--border); background: var(--bg2); display: flex; align-items: center; gap: 12px; }
.search { flex: 1; padding: 8px 14px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg); color: var(--fg); font-size: 14px; outline: none; }
.search:focus { border-color: var(--accent); }
.stats { font-size: 13px; color: var(--fg2); white-space: nowrap; }
.content { flex: 1; overflow-y: auto; padding: 20px; }
.empty { text-align: center; padding: 60px 20px; color: var(--fg3); }
.empty h3 { margin-bottom: 8px; }
.skill-card { background: var(--bg2); border: 1px solid var(--border); border-radius: 12px; padding: 16px; margin-bottom: 12px; box-shadow: var(--card-shadow); }
.skill-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
.skill-name { font-size: 16px; font-weight: 600; }
.skill-version { font-size: 12px; color: var(--fg3); background: var(--bg3); padding: 2px 8px; border-radius: 10px; }
.skill-desc { font-size: 14px; color: var(--fg2); margin-bottom: 10px; }
.skill-meta { display: flex; gap: 16px; font-size: 12px; color: var(--fg3); margin-bottom: 10px; }
.skill-tags { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 12px; }
.tag { font-size: 11px; padding: 2px 8px; border-radius: 6px; background: var(--tag-bg); color: var(--tag-fg); }
.skill-actions { display: flex; gap: 8px; }
.btn { padding: 6px 14px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg); color: var(--fg); cursor: pointer; font-size: 13px; }
.btn:hover { background: var(--bg3); }
.btn-primary { background: var(--accent); color: white; border-color: var(--accent); }
.btn-primary:hover { background: var(--accent2); }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: none; z-index: 100; align-items: center; justify-content: center; }
.modal-overlay.open { display: flex; }
.modal { background: var(--bg2); border-radius: 12px; width: 90%; max-width: 900px; max-height: 85vh; display: flex; flex-direction: column; box-shadow: 0 8px 32px rgba(0,0,0,0.2); }
.modal-header { padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
.modal-header h3 { font-size: 16px; }
.modal-close { background: none; border: none; font-size: 20px; cursor: pointer; color: var(--fg); padding: 4px 8px; }
.modal-body { flex: 1; overflow-y: auto; padding: 20px; }
.md-content h1 { font-size: 22px; margin: 16px 0 8px; border-bottom: 1px solid var(--border); padding-bottom: 6px; }
.md-content h2 { font-size: 18px; margin: 14px 0 6px; }
.md-content h3 { font-size: 15px; margin: 12px 0 4px; }
.md-content p { margin: 8px 0; line-height: 1.6; }
.md-content ul, .md-content ol { margin: 8px 0 8px 24px; }
.md-content li { margin: 4px 0; line-height: 1.5; }
.md-content code { background: var(--code-bg); padding: 2px 6px; border-radius: 4px; font-size: 13px; font-family: 'SF Mono', Consolas, monospace; }
.md-content pre { background: var(--code-bg); padding: 14px; border-radius: 8px; overflow-x: auto; margin: 10px 0; }
.md-content pre code { background: none; padding: 0; }
.md-content a { color: var(--accent); }
.md-content strong { font-weight: 600; }
.md-content em { font-style: italic; }
.md-content hr { border: none; border-top: 1px solid var(--border); margin: 16px 0; }
.history-panel { margin-top: 12px; border-top: 1px solid var(--border); padding-top: 12px; display: none; }
.history-panel.open { display: block; }
.version-list { display: flex; flex-direction: column; gap: 6px; }
.version-item { display: flex; align-items: center; gap: 10px; padding: 8px 12px; border-radius: 6px; cursor: pointer; font-size: 13px; }
.version-item:hover { background: var(--bg3); }
.version-item.current { font-weight: 600; }
.version-badge { font-size: 11px; padding: 2px 8px; border-radius: 10px; background: var(--bg3); }
.version-badge.current { background: var(--accent); color: white; }
.diff-view { margin-top: 12px; border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
.diff-header { padding: 8px 12px; background: var(--bg3); font-size: 13px; font-weight: 600; border-bottom: 1px solid var(--border); }
.diff-line { padding: 2px 12px; font-family: 'SF Mono', Consolas, monospace; font-size: 12px; white-space: pre-wrap; word-break: break-all; }
.diff-add { background: var(--diff-add); color: var(--diff-add-fg); }
.diff-rm { background: var(--diff-rm); color: var(--diff-rm-fg); }
.diff-ctx { color: var(--fg3); }
.project-path { font-size: 11px; color: var(--fg3); margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.generated { padding: 8px 16px; font-size: 11px; color: var(--fg3); border-top: 1px solid var(--border); }
</style>
</head>
<body>
<div class="sidebar">
  <div class="sidebar-header">
    <h2>Skilltrace</h2>
    <button class="theme-btn" onclick="toggleTheme()" title="Toggle theme">&#9681;</button>
  </div>
  <div class="project-list" id="projectList"></div>
  <div class="generated" id="generated"></div>
</div>
<div class="main">
  <div class="topbar">
    <input class="search" id="search" type="text" placeholder="Search skills...">
    <span class="stats" id="stats"></span>
  </div>
  <div class="content" id="content"></div>
</div>
<div class="modal-overlay" id="modal" onclick="if(event.target===this)closeModal()">
  <div class="modal">
    <div class="modal-header">
      <h3 id="modalTitle"></h3>
      <button class="modal-close" onclick="closeModal()">&times;</button>
    </div>
    <div class="modal-body md-content" id="modalBody"></div>
  </div>
</div>
<script>
const DATA = __DATA__;

let currentProject = null;
let searchQuery = '';

function init() {
  const theme = localStorage.getItem('st-theme') || 'light';
  document.documentElement.setAttribute('data-theme', theme);
  document.getElementById('generated').textContent = 'Generated: ' + DATA.generated;
  renderProjects();
  renderSkills();
  document.getElementById('search').addEventListener('input', e => {
    searchQuery = e.target.value.toLowerCase();
    renderSkills();
  });
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('st-theme', next);
}

function renderProjects() {
  const el = document.getElementById('projectList');
  const totalSkills = DATA.projects.reduce((a, p) => a + p.skills.length, 0);
  let html = `<div class="project-item ${currentProject === null ? 'active' : ''}" onclick="selectProject(null)">
    <span>All Projects</span><span class="count">${totalSkills}</span></div>`;
  for (const p of DATA.projects) {
    const active = currentProject === p.id ? 'active' : '';
    html += `<div class="project-item ${active}" onclick="selectProject('${p.id}')">
      <div><div>${esc(p.name)}</div><div class="project-path">${esc(p.path)}</div></div>
      <span class="count">${p.skills.length}</span></div>`;
  }
  el.innerHTML = html;
}

function selectProject(id) {
  currentProject = id;
  renderProjects();
  renderSkills();
}

function getFilteredSkills() {
  let skills = [];
  for (const p of DATA.projects) {
    if (currentProject && p.id !== currentProject) continue;
    for (const s of p.skills) {
      skills.push({...s, projectName: p.name, projectId: p.id, projectPath: p.path});
    }
  }
  if (searchQuery) {
    skills = skills.filter(s =>
      s.name.toLowerCase().includes(searchQuery) ||
      s.description.toLowerCase().includes(searchQuery) ||
      s.id.toLowerCase().includes(searchQuery) ||
      (s.tags || []).some(t => t.toLowerCase().includes(searchQuery))
    );
  }
  return skills;
}

function renderSkills() {
  const skills = getFilteredSkills();
  const el = document.getElementById('content');
  const totalProjects = new Set(skills.map(s => s.projectId)).size;
  document.getElementById('stats').textContent = `${skills.length} skill${skills.length !== 1 ? 's' : ''} in ${totalProjects} project${totalProjects !== 1 ? 's' : ''}`;
  if (!skills.length) {
    el.innerHTML = '<div class="empty"><h3>No skills found</h3><p>Skills will appear here as Skilltrace generates them.</p></div>';
    return;
  }
  el.innerHTML = skills.map((s, i) => {
    const tags = (s.tags || []).map(t => `<span class="tag">${esc(t)}</span>`).join('');
    const proj = currentProject ? '' : `<span>${esc(s.projectName)}</span>`;
    return `<div class="skill-card" id="card-${i}">
      <div class="skill-header">
        <span class="skill-name">${esc(s.name)}</span>
        <span class="skill-version">v${s.current_version}</span>
      </div>
      ${s.description ? `<div class="skill-desc">${esc(s.description)}</div>` : ''}
      <div class="skill-meta">
        ${proj}
        <span>Created: ${fmtDate(s.created)}</span>
        <span>Updated: ${fmtDate(s.updated)}</span>
      </div>
      ${tags ? `<div class="skill-tags">${tags}</div>` : ''}
      <div class="skill-actions">
        <button class="btn btn-primary" onclick="viewSkill(${i})">View</button>
        ${s.versions.length > 1 ? `<button class="btn" onclick="toggleHistory(${i})">History</button>` : ''}
      </div>
      <div class="history-panel" id="history-${i}">
        ${renderHistory(s, i)}
      </div>
    </div>`;
  }).join('');
}

function renderHistory(skill, cardIdx) {
  if (!skill.versions.length) return '<p>No versions</p>';
  let html = '<div class="version-list">';
  for (let v = skill.versions.length - 1; v >= 0; v--) {
    const ver = skill.versions[v];
    const isCurrent = ver.current ? 'current' : '';
    const badge = ver.current ? 'current' : '';
    html += `<div class="version-item ${isCurrent}" onclick="viewVersion(${cardIdx}, ${v})">
      <span class="version-badge ${badge}">v${ver.version}</span>
      <span>${ver.current ? 'Current' : 'Archived'}</span>
      ${v > 0 ? `<button class="btn" style="margin-left:auto;font-size:11px" onclick="event.stopPropagation();showDiff(${cardIdx},${v-1},${v})">Diff with v${skill.versions[v-1].version}</button>` : ''}
    </div>`;
  }
  html += '</div><div id="diff-area-' + cardIdx + '"></div>';
  return html;
}

function toggleHistory(idx) {
  const el = document.getElementById('history-' + idx);
  el.classList.toggle('open');
}

function viewSkill(idx) {
  const skills = getFilteredSkills();
  const s = skills[idx];
  const current = s.versions.find(v => v.current);
  if (!current) return;
  document.getElementById('modalTitle').textContent = s.name + ' (v' + s.current_version + ')';
  document.getElementById('modalBody').innerHTML = renderMd(current.content);
  document.getElementById('modal').classList.add('open');
}

function viewVersion(cardIdx, vIdx) {
  const skills = getFilteredSkills();
  const s = skills[cardIdx];
  const ver = s.versions[vIdx];
  document.getElementById('modalTitle').textContent = s.name + ' (v' + ver.version + ')';
  document.getElementById('modalBody').innerHTML = renderMd(ver.content);
  document.getElementById('modal').classList.add('open');
}

function closeModal() {
  document.getElementById('modal').classList.remove('open');
}

function showDiff(cardIdx, aIdx, bIdx) {
  const skills = getFilteredSkills();
  const s = skills[cardIdx];
  const a = s.versions[aIdx].content;
  const b = s.versions[bIdx].content;
  const diff = lineDiff(a, b);
  const area = document.getElementById('diff-area-' + cardIdx);
  let html = `<div class="diff-view"><div class="diff-header">v${s.versions[aIdx].version} → v${s.versions[bIdx].version}</div>`;
  for (const line of diff) {
    if (line.type === 'add') html += `<div class="diff-line diff-add">+ ${esc(line.text)}</div>`;
    else if (line.type === 'rm') html += `<div class="diff-line diff-rm">- ${esc(line.text)}</div>`;
    else html += `<div class="diff-line diff-ctx">  ${esc(line.text)}</div>`;
  }
  html += '</div>';
  area.innerHTML = html;
}

// --- Markdown renderer (no deps) ---
function renderMd(text) {
  if (!text) return '';
  const lines = text.split('\n');
  let html = '', inCode = false, codeBuf = [], inList = false, listType = '';

  function flushList() {
    if (inList) { html += listType === 'ol' ? '</ol>' : '</ul>'; inList = false; }
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line.startsWith('```')) {
      if (inCode) { html += '<pre><code>' + esc(codeBuf.join('\n')) + '</code></pre>'; codeBuf = []; inCode = false; }
      else { flushList(); inCode = true; }
      continue;
    }
    if (inCode) { codeBuf.push(line); continue; }
    if (line.startsWith('---') && line.trim() === '---') {
      if (i < 3) continue; // skip frontmatter delimiter
      flushList(); html += '<hr>'; continue;
    }
    if (/^#{1,6}\s/.test(line)) {
      flushList();
      const lvl = line.match(/^(#+)/)[1].length;
      html += `<h${lvl}>${inline(line.replace(/^#+\s*/, ''))}</h${lvl}>`;
      continue;
    }
    if (/^[\-\*]\s/.test(line)) {
      if (!inList || listType !== 'ul') { flushList(); html += '<ul>'; inList = true; listType = 'ul'; }
      html += `<li>${inline(line.replace(/^[\-\*]\s*/, ''))}</li>`;
      continue;
    }
    if (/^\d+\.\s/.test(line)) {
      if (!inList || listType !== 'ol') { flushList(); html += '<ol>'; inList = true; listType = 'ol'; }
      html += `<li>${inline(line.replace(/^\d+\.\s*/, ''))}</li>`;
      continue;
    }
    flushList();
    if (line.trim() === '') { html += ''; continue; }
    // skip frontmatter key: value lines at top
    if (i < 5 && /^[a-z_]+:/.test(line)) continue;
    html += `<p>${inline(line)}</p>`;
  }
  flushList();
  if (inCode) html += '<pre><code>' + esc(codeBuf.join('\n')) + '</code></pre>';
  return html;
}

function inline(text) {
  return text
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
}

// --- Line diff (no deps) ---
function lineDiff(a, b) {
  const la = a.split('\n'), lb = b.split('\n');
  const n = la.length, m = lb.length;
  const max = n + m;
  const v = new Array(2 * max + 1).fill(0);
  const trace = [];
  for (let d = 0; d <= max; d++) {
    trace.push([...v]);
    for (let k = -d; k <= d; k += 2) {
      let x;
      if (k === -d || (k !== d && v[k - 1 + max] < v[k + 1 + max])) x = v[k + 1 + max];
      else x = v[k - 1 + max] + 1;
      let y = x - k;
      while (x < n && y < m && la[x] === lb[y]) { x++; y++; }
      v[k + max] = x;
      if (x >= n && y >= m) {
        return buildDiff(la, lb, trace, d, max);
      }
    }
  }
  return la.map(t => ({type: 'rm', text: t})).concat(lb.map(t => ({type: 'add', text: t})));
}

function buildDiff(la, lb, trace, D, max) {
  let x = la.length, y = lb.length;
  const edits = [];
  for (let d = D; d > 0; d--) {
    const v = trace[d - 1];
    const k = x - y;
    let prevK;
    if (k === -d || (k !== d && v[k - 1 + max] < v[k + 1 + max])) prevK = k + 1;
    else prevK = k - 1;
    const prevX = v[prevK + max];
    const prevY = prevX - prevK;
    while (x > prevX && y > prevY) { x--; y--; edits.unshift({type: 'ctx', text: la[x]}); }
    if (x > prevX) { x--; edits.unshift({type: 'rm', text: la[x]}); }
    else if (y > prevY) { y--; edits.unshift({type: 'add', text: lb[y]}); }
  }
  while (x > 0 && y > 0) { x--; y--; edits.unshift({type: 'ctx', text: la[x]}); }
  return edits;
}

function esc(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function fmtDate(s) { if (!s) return '—'; try { return new Date(s).toLocaleDateString('en-GB', {day:'numeric',month:'short',year:'numeric'}); } catch(e) { return s; } }

document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });
init();
</script>
</body>
</html>"""


def generate(no_open: bool = False) -> dict:
    data = _collect_data()
    data_json = json.dumps(data, ensure_ascii=False)
    html = _HTML_TEMPLATE.replace("__DATA__", data_json)

    out_dir = skilltrace_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "dashboard.html"
    tmp_path = out_path.with_suffix(".tmp")
    tmp_path.write_text(html, encoding="utf-8")
    tmp_path.replace(out_path)

    total_skills = sum(len(p["skills"]) for p in data["projects"])

    if not no_open:
        webbrowser.open(out_path.as_uri())

    return {
        "status": "ok",
        "action": "dashboard_generated",
        "path": str(out_path),
        "ts": data["generated"],
        "projects": len(data["projects"]),
        "skills": total_skills,
    }
