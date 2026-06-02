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
    candidates = [
        Path(project_path) / ".claude" / "skills" / skill_id / "SKILL.md",
        Path.home() / ".claude" / "skills" / skill_id / "SKILL.md",
    ]
    for p in candidates:
        if p.exists():
            try:
                return p.read_text(encoding="utf-8")
            except OSError:
                pass
    return ""


def _read_versions(project_path: str, skill_id: str, current_version: int) -> list[dict]:
    versions = []
    ver_bases = [
        Path(project_path) / ".claude" / "skilltrace" / "versions" / skill_id,
        Path.home() / ".claude" / "skilltrace" / "versions" / skill_id,
    ]
    for v in range(1, current_version):
        for ver_base in ver_bases:
            vpath = ver_base / f"v{v}.md"
            if vpath.exists():
                try:
                    versions.append({"version": v, "content": vpath.read_text(encoding="utf-8")})
                except OSError:
                    pass
                break
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
  --bg: #fafaf8; --bg2: #ffffff; --bg3: #e8f4fd;
  --fg: #1b4965; --fg2: #3a6b8a; --fg3: #7a9bb5;
  --accent: #5fa8d3; --accent2: #4a93be; --accent-dark: #1b4965;
  --border: #d1dbe5; --card-shadow: 0 2px 8px rgba(27,73,101,0.06);
  --diff-add: #e6f5ec; --diff-rm: #fbe8e8;
  --diff-add-fg: #1a5c32; --diff-rm-fg: #8b2525;
  --code-bg: #f0f4f8; --tag-bg: #e8f4fd; --tag-fg: #1b4965;
  --sidebar-w: 280px;
  --radius: 12px;
}
[data-theme="dark"] {
  --bg: #0c1620; --bg2: #132232; --bg3: #1a3042;
  --fg: #dce8f0; --fg2: #94b3c8; --fg3: #5a7a90;
  --accent: #5fa8d3; --accent2: #7bbde0; --accent-dark: #dce8f0;
  --border: #1e3a50; --card-shadow: 0 2px 8px rgba(0,0,0,0.3);
  --diff-add: #0f2a1a; --diff-rm: #2a0f0f;
  --diff-add-fg: #6ee7b7; --diff-rm-fg: #fca5a5;
  --code-bg: #1a2e3e; --tag-bg: #1a3042; --tag-fg: #5fa8d3;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif; background: var(--bg); color: var(--fg); display: flex; height: 100vh; overflow: hidden; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

/* Sidebar */
.sidebar { width: var(--sidebar-w); background: var(--bg2); border-right: 1px solid var(--border); display: flex; flex-direction: column; flex-shrink: 0; }
.sidebar-header { padding: 20px; border-bottom: 1px solid var(--border); }
.sidebar-brand { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
.sidebar-brand h2 { font-size: 18px; font-weight: 700; color: var(--accent-dark); letter-spacing: -0.3px; }
.sidebar-brand h2 span { color: var(--accent); }
.theme-btn { background: none; border: 1px solid var(--border); border-radius: 8px; width: 32px; height: 32px; cursor: pointer; color: var(--fg2); font-size: 15px; display: flex; align-items: center; justify-content: center; transition: all 0.2s; }
.theme-btn:hover { background: var(--bg3); border-color: var(--accent); }
.sidebar-link { font-size: 11px; color: var(--fg3); }
.sidebar-link a { color: var(--accent); font-size: 11px; }
.project-list { flex: 1; overflow-y: auto; padding: 12px; }
.project-item { padding: 12px 14px; border-radius: 10px; cursor: pointer; margin-bottom: 4px; display: flex; justify-content: space-between; align-items: center; font-size: 14px; transition: all 0.15s; }
.project-item:hover { background: var(--bg3); }
.project-item.active { background: var(--accent); color: white; }
.project-info { flex: 1; min-width: 0; }
.project-name { font-weight: 500; }
.project-path { font-size: 11px; color: var(--fg3); margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 180px; }
.project-item.active .project-path { color: rgba(255,255,255,0.7); }
.count { font-size: 11px; font-weight: 600; background: var(--bg3); color: var(--fg2); border-radius: 12px; padding: 3px 10px; flex-shrink: 0; margin-left: 8px; }
.project-item.active .count { background: rgba(255,255,255,0.2); color: white; }
.sidebar-footer { padding: 12px 16px; font-size: 11px; color: var(--fg3); border-top: 1px solid var(--border); }

/* Main */
.main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.topbar { padding: 14px 24px; border-bottom: 1px solid var(--border); background: var(--bg2); display: flex; align-items: center; gap: 14px; }
.search { flex: 1; padding: 10px 16px; border: 1px solid var(--border); border-radius: 10px; background: var(--bg); color: var(--fg); font-size: 14px; outline: none; transition: border 0.2s; }
.search:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(95,168,211,0.15); }
.content { flex: 1; overflow-y: auto; padding: 24px; }
.empty { text-align: center; padding: 80px 20px; color: var(--fg3); }
.empty h3 { font-size: 18px; margin-bottom: 8px; color: var(--fg2); }

/* Skill Cards */
.skill-card { background: var(--bg2); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px; margin-bottom: 14px; box-shadow: var(--card-shadow); transition: box-shadow 0.2s; }
.skill-card:hover { box-shadow: 0 4px 16px rgba(27,73,101,0.1); }
.skill-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px; }
.skill-name { font-size: 17px; font-weight: 600; color: var(--accent-dark); }
.skill-version { font-size: 11px; font-weight: 600; color: var(--accent); background: var(--bg3); padding: 4px 10px; border-radius: 12px; flex-shrink: 0; }
.skill-desc { font-size: 14px; color: var(--fg2); margin-bottom: 12px; line-height: 1.5; }
.skill-meta { display: flex; flex-wrap: wrap; gap: 16px; font-size: 12px; color: var(--fg3); margin-bottom: 12px; }
.skill-tags { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 14px; }
.tag { font-size: 11px; padding: 3px 10px; border-radius: 8px; background: var(--tag-bg); color: var(--tag-fg); font-weight: 500; border: 1px solid var(--border); }
.skill-actions { display: flex; gap: 8px; }
.btn { padding: 7px 16px; border-radius: 8px; border: 1px solid var(--border); background: var(--bg2); color: var(--fg); cursor: pointer; font-size: 13px; font-weight: 500; transition: all 0.15s; }
.btn:hover { background: var(--bg3); border-color: var(--accent); }
.btn-primary { background: var(--accent); color: white; border-color: var(--accent); }
.btn-primary:hover { background: var(--accent2); }

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(12,22,32,0.6); display: none; z-index: 100; align-items: center; justify-content: center; backdrop-filter: blur(2px); }
.modal-overlay.open { display: flex; }
.modal { background: var(--bg2); border-radius: 16px; width: 94%; max-width: 1100px; max-height: 90vh; display: flex; flex-direction: column; box-shadow: 0 12px 48px rgba(27,73,101,0.2); border: 1px solid var(--border); }
.modal-header { padding: 16px 24px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
.modal-header h3 { font-size: 17px; font-weight: 600; color: var(--accent-dark); }
.modal-close { background: none; border: 1px solid var(--border); border-radius: 8px; width: 32px; height: 32px; font-size: 18px; cursor: pointer; color: var(--fg2); display: flex; align-items: center; justify-content: center; transition: all 0.15s; }
.modal-close:hover { background: var(--bg3); border-color: var(--accent); }
.modal-tabs { display: flex; border-bottom: 1px solid var(--border); padding: 0 24px; }
.modal-tab { padding: 10px 18px; font-size: 13px; font-weight: 500; color: var(--fg3); cursor: pointer; border-bottom: 2px solid transparent; transition: all 0.15s; }
.modal-tab:hover { color: var(--fg); }
.modal-tab.active { color: var(--accent); border-bottom-color: var(--accent); }
.modal-body { flex: 1; overflow-y: auto; padding: 24px; }
.tab-content { display: none; }
.tab-content.active { display: block; }

/* Compare controls */
.compare-controls { display: flex; gap: 12px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }
.compare-controls label { font-size: 13px; color: var(--fg2); font-weight: 500; }
.compare-controls select { padding: 6px 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg); color: var(--fg); font-size: 13px; }
.compare-mode { display: flex; gap: 4px; }
.compare-mode button { padding: 5px 12px; border: 1px solid var(--border); background: var(--bg); color: var(--fg2); cursor: pointer; font-size: 12px; }
.compare-mode button:first-child { border-radius: 6px 0 0 6px; }
.compare-mode button:last-child { border-radius: 0 6px 6px 0; }
.compare-mode button.active { background: var(--accent); color: white; border-color: var(--accent); }

/* Side-by-side diff */
.diff-side { display: flex; border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
.diff-pane { flex: 1; overflow-x: auto; }
.diff-pane-header { padding: 8px 14px; background: var(--bg3); font-size: 12px; font-weight: 600; color: var(--accent-dark); border-bottom: 1px solid var(--border); }
.diff-pane:first-child { border-right: 1px solid var(--border); }
.diff-pane-line { padding: 1px 14px; font-family: 'Cascadia Code', 'SF Mono', Consolas, monospace; font-size: 12px; white-space: pre-wrap; word-break: break-all; min-height: 20px; display: flex; }
.diff-pane-line .ln { color: var(--fg3); min-width: 32px; text-align: right; padding-right: 10px; user-select: none; opacity: 0.5; }
.diff-pane-line.diff-add { background: var(--diff-add); color: var(--diff-add-fg); }
.diff-pane-line.diff-rm { background: var(--diff-rm); color: var(--diff-rm-fg); }
.diff-pane-line.diff-empty { background: var(--bg3); opacity: 0.3; }

/* Version timeline */
.timeline { display: flex; flex-direction: column; gap: 2px; }
.timeline-item { display: flex; align-items: stretch; gap: 14px; cursor: pointer; padding: 12px 14px; border-radius: 8px; transition: background 0.15s; }
.timeline-item:hover { background: var(--bg3); }
.timeline-dot-col { display: flex; flex-direction: column; align-items: center; width: 20px; }
.timeline-dot { width: 12px; height: 12px; border-radius: 50%; background: var(--border); flex-shrink: 0; margin-top: 4px; }
.timeline-dot.current { background: var(--accent); box-shadow: 0 0 0 3px rgba(95,168,211,0.25); }
.timeline-line { flex: 1; width: 2px; background: var(--border); margin-top: 4px; }
.timeline-info { flex: 1; }
.timeline-version { font-size: 14px; font-weight: 600; color: var(--accent-dark); }
.timeline-label { font-size: 12px; color: var(--fg3); margin-top: 2px; }
.timeline-item:last-child .timeline-line { display: none; }

/* Markdown */
.md-content h1 { font-size: 24px; font-weight: 700; color: var(--accent-dark); margin: 20px 0 10px; border-bottom: 2px solid var(--border); padding-bottom: 8px; }
.md-content h2 { font-size: 19px; font-weight: 600; color: var(--accent-dark); margin: 18px 0 8px; }
.md-content h3 { font-size: 16px; font-weight: 600; color: var(--fg); margin: 14px 0 6px; }
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

/* History */
.history-panel { margin-top: 14px; border-top: 1px solid var(--border); padding-top: 14px; display: none; }
.history-panel.open { display: block; }
.version-list { display: flex; flex-direction: column; gap: 4px; }
.version-item { display: flex; align-items: center; gap: 10px; padding: 10px 14px; border-radius: 8px; cursor: pointer; font-size: 13px; transition: background 0.15s; }
.version-item:hover { background: var(--bg3); }
.version-item.current { font-weight: 600; }
.version-badge { font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 10px; background: var(--bg3); color: var(--fg2); }
.version-badge.current { background: var(--accent); color: white; }
.diff-view { margin-top: 14px; border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
.diff-header { padding: 10px 14px; background: var(--bg3); font-size: 13px; font-weight: 600; color: var(--accent-dark); border-bottom: 1px solid var(--border); }
.diff-line { padding: 3px 14px; font-family: 'Cascadia Code', 'SF Mono', Consolas, monospace; font-size: 12px; white-space: pre-wrap; word-break: break-all; }
.diff-add { background: var(--diff-add); color: var(--diff-add-fg); }
.diff-rm { background: var(--diff-rm); color: var(--diff-rm-fg); }
.diff-ctx { color: var(--fg3); }

/* Responsive */
@media (max-width: 768px) {
  body { flex-direction: column; }
  .sidebar { width: 100%; height: auto; max-height: 40vh; border-right: none; border-bottom: 1px solid var(--border); }
  .project-path { max-width: 200px; }
  .content { padding: 16px; }
  .modal { width: 96%; max-height: 90vh; border-radius: 12px; }
}
</style>
</head>
<body>
<div class="sidebar">
  <div class="sidebar-header">
    <div class="sidebar-brand">
      <h2><span>/</span>skilltrace</h2>
      <button class="theme-btn" onclick="toggleTheme()" title="Toggle theme">&#9681;</button>
    </div>
    <div class="sidebar-link"><a href="https://www-skilltrace.vercel.app/" target="_blank">&#127760; Official Website</a></div>
  </div>
  <div class="project-list" id="projectList"></div>
  <div class="sidebar-footer" id="generated"></div>
</div>
<div class="main">
  <div class="topbar">
    <input class="search" id="search" type="text" placeholder="Search skills by name, tag, or description...">
  </div>
  <div class="content" id="content"></div>
</div>
<div class="modal-overlay" id="modal" onclick="if(event.target===this)closeModal()">
  <div class="modal">
    <div class="modal-header">
      <h3 id="modalTitle"></h3>
      <button class="modal-close" onclick="closeModal()">&times;</button>
    </div>
    <div class="modal-tabs" id="modalTabs"></div>
    <div class="modal-body">
      <div class="tab-content active" id="tabContent"></div>
      <div class="tab-content" id="tabHistory"></div>
      <div class="tab-content" id="tabCompare"></div>
    </div>
  </div>
</div>
<script>
const DATA = __DATA__;

let currentProject = null;
let searchQuery = '';

function init() {
  const theme = localStorage.getItem('st-theme') || 'light';
  document.documentElement.setAttribute('data-theme', theme);
  document.getElementById('generated').textContent = 'Generated: ' + new Date(DATA.generated).toLocaleString('en-GB', {day:'numeric',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'});
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
      </div>
    </div>`;
  }).join('');
}

let modalSkill = null;
let diffMode = 'side';

function toggleHistory(idx) {
  const el = document.getElementById('history-' + idx);
  el.classList.toggle('open');
}

function viewSkill(idx) {
  const skills = getFilteredSkills();
  modalSkill = skills[idx];
  const s = modalSkill;
  const current = s.versions.find(v => v.current);
  if (!current) return;
  document.getElementById('modalTitle').textContent = s.name;
  const hasManyVersions = s.versions.length > 1;
  let tabs = `<div class="modal-tab active" onclick="switchTab('content')">Content (v${s.current_version})</div>`;
  if (hasManyVersions) {
    tabs += `<div class="modal-tab" onclick="switchTab('history')">History (${s.versions.length})</div>`;
    tabs += `<div class="modal-tab" onclick="switchTab('compare')">Compare</div>`;
  }
  document.getElementById('modalTabs').innerHTML = tabs;
  document.getElementById('tabContent').className = 'tab-content active md-content';
  document.getElementById('tabContent').innerHTML = renderMd(current.content);
  if (hasManyVersions) {
    renderTimeline();
    renderCompare();
  }
  document.getElementById('tabHistory').className = 'tab-content';
  document.getElementById('tabCompare').className = 'tab-content';
  document.getElementById('modal').classList.add('open');
}

function switchTab(name) {
  document.querySelectorAll('.modal-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  event.target.classList.add('active');
  const map = {content: 'tabContent', history: 'tabHistory', compare: 'tabCompare'};
  const el = document.getElementById(map[name]);
  if (el) { el.classList.add('active'); if (name === 'history') el.classList.add('md-content'); }
}

function renderTimeline() {
  const s = modalSkill;
  let html = '<div class="timeline">';
  for (let i = s.versions.length - 1; i >= 0; i--) {
    const v = s.versions[i];
    const isCurrent = v.current ? 'current' : '';
    html += `<div class="timeline-item" onclick="showVersionInModal(${i})">
      <div class="timeline-dot-col"><div class="timeline-dot ${isCurrent}"></div><div class="timeline-line"></div></div>
      <div class="timeline-info">
        <div class="timeline-version">Version ${v.version} ${v.current ? '(current)' : ''}</div>
        <div class="timeline-label">${v.current ? 'Latest' : 'Archived'} — click to view</div>
      </div>
    </div>`;
  }
  html += '</div>';
  document.getElementById('tabHistory').innerHTML = html;
}

function showVersionInModal(vIdx) {
  const v = modalSkill.versions[vIdx];
  document.getElementById('tabContent').innerHTML = renderMd(v.content);
  document.querySelectorAll('.modal-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  const contentTab = document.querySelector('.modal-tab');
  contentTab.classList.add('active');
  contentTab.textContent = 'Content (v' + v.version + ')';
  document.getElementById('tabContent').classList.add('active');
}

function renderCompare() {
  const s = modalSkill;
  const vers = s.versions;
  let optionsA = '', optionsB = '';
  for (let i = 0; i < vers.length; i++) {
    const sel = i === Math.max(0, vers.length - 2) ? 'selected' : '';
    optionsA += `<option value="${i}" ${sel}>v${vers[i].version}${vers[i].current ? ' (current)' : ''}</option>`;
  }
  for (let i = 0; i < vers.length; i++) {
    const sel = i === vers.length - 1 ? 'selected' : '';
    optionsB += `<option value="${i}" ${sel}>v${vers[i].version}${vers[i].current ? ' (current)' : ''}</option>`;
  }
  let html = `<div class="compare-controls">
    <label>From</label><select id="diffA" onchange="updateDiff()">${optionsA}</select>
    <button class="btn" onclick="swapDiff()" title="Swap versions" style="padding:5px 10px;font-size:14px">&#8646;</button>
    <label>To</label><select id="diffB" onchange="updateDiff()">${optionsB}</select>
    <div class="compare-mode">
      <button class="${diffMode==='side'?'active':''}" onclick="setDiffMode('side')">Side by side</button>
      <button class="${diffMode==='inline'?'active':''}" onclick="setDiffMode('inline')">Inline</button>
    </div>
  </div><div id="diffOutput"></div>`;
  document.getElementById('tabCompare').innerHTML = html;
  updateDiff();
}

function swapDiff() {
  const a = document.getElementById('diffA');
  const b = document.getElementById('diffB');
  const tmp = a.value;
  a.value = b.value;
  b.value = tmp;
  updateDiff();
}

function setDiffMode(mode) {
  diffMode = mode;
  document.querySelectorAll('.compare-mode button').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  updateDiff();
}

function updateDiff() {
  const aIdx = parseInt(document.getElementById('diffA').value);
  const bIdx = parseInt(document.getElementById('diffB').value);
  const a = modalSkill.versions[aIdx].content || '';
  const b = modalSkill.versions[bIdx].content || '';
  const diff = lineDiff(a, b);
  const vA = modalSkill.versions[aIdx].version;
  const vB = modalSkill.versions[bIdx].version;
  document.getElementById('diffOutput').innerHTML = diffMode === 'side' ? renderSideDiff(diff, vA, vB) : renderInlineDiff(diff, vA, vB);
}

function renderSideDiff(diff, vA, vB) {
  let leftLines = [], rightLines = [];
  let lnA = 1, lnB = 1;
  for (const d of diff) {
    if (d.type === 'ctx') {
      leftLines.push({ln: lnA++, text: d.text, cls: ''});
      rightLines.push({ln: lnB++, text: d.text, cls: ''});
    } else if (d.type === 'rm') {
      leftLines.push({ln: lnA++, text: d.text, cls: 'diff-rm'});
      rightLines.push({ln: '', text: '', cls: 'diff-empty'});
    } else {
      leftLines.push({ln: '', text: '', cls: 'diff-empty'});
      rightLines.push({ln: lnB++, text: d.text, cls: 'diff-add'});
    }
  }
  const renderPane = (lines) => lines.map(l => `<div class="diff-pane-line ${l.cls}"><span class="ln">${l.ln}</span><span>${esc(l.text)}</span></div>`).join('');
  return `<div class="diff-side">
    <div class="diff-pane"><div class="diff-pane-header">v${vA}</div>${renderPane(leftLines)}</div>
    <div class="diff-pane"><div class="diff-pane-header">v${vB}</div>${renderPane(rightLines)}</div>
  </div>`;
}

function renderInlineDiff(diff, vA, vB) {
  let html = `<div class="diff-view"><div class="diff-header">v${vA} → v${vB}</div>`;
  for (const d of diff) {
    if (d.type === 'add') html += `<div class="diff-line diff-add">+ ${esc(d.text)}</div>`;
    else if (d.type === 'rm') html += `<div class="diff-line diff-rm">- ${esc(d.text)}</div>`;
    else html += `<div class="diff-line diff-ctx">  ${esc(d.text)}</div>`;
  }
  return html + '</div>';
}

function viewVersion(cardIdx, vIdx) {
  viewSkill(cardIdx);
  showVersionInModal(vIdx);
}

function closeModal() {
  document.getElementById('modal').classList.remove('open');
  modalSkill = null;
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
    import os
    os.replace(str(tmp_path), str(out_path))

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
