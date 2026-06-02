"""Skillforge Dashboard — generates a static HTML viewer for all projects and skills.

Scans home directory for .claude/skillforge/registry.json files,
reads skill files, outputs a self-contained HTML and opens it in the browser.
"""

import json
import os
import re
import time
import webbrowser
from pathlib import Path

from src.shared import skillforge_dir, skills_dir, now_iso

_MAX_DEPTH = 10
_SCAN_TIMEOUT = 120
_MAX_VERSIONS = 50
_SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".tox", ".mypy_cache", ".pytest_cache", "dist", "build",
    ".next", ".nuxt", "target", "bin", "obj", ".cache",
    "AppData", "Application Data", ".npm", ".yarn",
}


def _is_safe_skill_id(sid: str) -> bool:
    return bool(sid) and bool(re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$", sid))


def _find_projects() -> list[dict]:
    projects = []
    seen_paths = set()
    scan_start = time.monotonic()

    def _walk(directory: Path, depth: int):
        if depth > _MAX_DEPTH:
            return
        if time.monotonic() - scan_start > _SCAN_TIMEOUT:
            return
        try:
            entries = sorted(directory.iterdir())
        except (PermissionError, OSError):
            return
        for entry in entries:
            if entry.is_symlink():
                continue
            if not entry.is_dir():
                continue
            if entry.name.startswith(".") and entry.name != ".claude":
                continue
            if entry.name in _SKIP_DIRS:
                continue
            if entry.name == ".claude":
                reg_path = entry / "skillforge" / "registry.json"
                if reg_path.exists():
                    project_path = str(entry.parent)
                    if project_path not in seen_paths:
                        seen_paths.add(project_path)
                        try:
                            reg = json.loads(reg_path.read_text(encoding="utf-8"))
                            skill_count = len(reg.get("skills", []))
                            projects.append({
                                "name": entry.parent.name,
                                "path": project_path,
                                "registry_path": str(reg_path),
                                "skills": reg.get("skills", []),
                            })
                        except (json.JSONDecodeError, OSError):
                            pass
                continue
            _walk(entry, depth + 1)

    _walk(Path.home(), 0)
    return projects


def _read_skill_content(project_path: str, skill_id: str) -> str:
    if not _is_safe_skill_id(skill_id):
        return ""
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
    if not _is_safe_skill_id(skill_id):
        return []
    versions = []
    start_version = max(1, current_version - _MAX_VERSIONS)
    ver_base = Path(project_path) / ".claude" / "skillforge" / "versions" / skill_id
    for v in range(start_version, current_version):
        vpath = ver_base / f"v{v}.md"
        if vpath.exists():
            try:
                versions.append({"version": v, "content": vpath.read_text(encoding="utf-8")})
            except OSError:
                pass
    current_content = _read_skill_content(project_path, skill_id)
    if current_content:
        versions.append({"version": current_version, "content": current_content, "current": True})
    if start_version > 1:
        versions.insert(0, {"version": 0, "capped": True, "hidden_count": start_version - 1})
    return versions


def _collect_data() -> dict:
    projects = _find_projects()
    result_projects = []
    for proj in projects:
        enriched_skills = []
        for s in proj["skills"]:
            sid = s.get("id", "")
            if not _is_safe_skill_id(sid):
                continue
            ver = s.get("version", 1)
            skill_content = _read_skill_content(proj["path"], sid)
            if not skill_content:
                continue
            enriched_skills.append({
                "id": sid,
                "name": s.get("name", sid),
                "description": s.get("description", ""),
                "tags": s.get("tags", []),
                "category": s.get("category", ""),
                "current_version": ver,
                "created": s.get("created", ""),
                "updated": s.get("updated", ""),
                "versions": _read_versions(proj["path"], sid, ver),
                "version_history": s.get("version_history", []),
            })
        result_projects.append({
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
<title>Skillforge Dashboard</title>
<style>
:root {
  --bg: #faf8f5; --bg2: #ffffff; --bg3: #f5ede6;
  --fg: #4a2c2a; --fg2: #6b4a48; --fg3: #9a7d7b;
  --accent: #c0392b; --accent2: #a93226; --accent-dark: #4a2c2a;
  --border: #ddd0c8; --card-shadow: 0 2px 8px rgba(74,44,42,0.06);
  --diff-add: #e6f5ec; --diff-rm: #fbe8e8;
  --diff-add-fg: #1a5c32; --diff-rm-fg: #8b2525;
  --code-bg: #f5ede6; --tag-bg: #f5ede6; --tag-fg: #4a2c2a;
  --sidebar-w: 280px; --radius: 12px;
}
[data-theme="dark"] {
  --bg: #1a0f0e; --bg2: #261816; --bg3: #3a2220;
  --fg: #f0dcd8; --fg2: #c8a8a4; --fg3: #7a5a58;
  --accent: #e74c3c; --accent2: #f06050; --accent-dark: #f0dcd8;
  --border: #3a2a28; --card-shadow: 0 2px 8px rgba(0,0,0,0.3);
  --diff-add: #0f2a1a; --diff-rm: #2a0f0f;
  --diff-add-fg: #6ee7b7; --diff-rm-fg: #fca5a5;
  --code-bg: #2a1a18; --tag-bg: #3a2220; --tag-fg: #e74c3c;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif; background: var(--bg); color: var(--fg); display: flex; height: 100vh; overflow: hidden; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
.sidebar { width: var(--sidebar-w); background: var(--bg2); border-right: 1px solid var(--border); display: flex; flex-direction: column; flex-shrink: 0; }
.sidebar-header { padding: 20px; border-bottom: 1px solid var(--border); }
.sidebar-brand { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
.sidebar-brand h2 { font-size: 18px; font-weight: 700; color: var(--accent-dark); letter-spacing: -0.3px; }
.sidebar-brand h2 span { color: var(--accent); }
.theme-btn { background: none; border: 1px solid var(--border); border-radius: 8px; width: 32px; height: 32px; cursor: pointer; color: var(--fg2); font-size: 15px; display: flex; align-items: center; justify-content: center; transition: all 0.2s; }
.theme-btn:hover { background: var(--bg3); border-color: var(--accent); }
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
.main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.topbar { padding: 14px 24px; border-bottom: 1px solid var(--border); background: var(--bg2); display: flex; align-items: center; gap: 14px; }
.hamburger { display: none; background: none; border: 1px solid var(--border); border-radius: 8px; width: 36px; height: 36px; cursor: pointer; color: var(--fg); font-size: 20px; align-items: center; justify-content: center; flex-shrink: 0; }
.search { flex: 1; padding: 10px 16px; border: 1px solid var(--border); border-radius: 10px; background: var(--bg); color: var(--fg); font-size: 14px; outline: none; transition: border 0.2s; }
.search:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(192,57,43,0.15); }
.content { flex: 1; overflow-y: auto; padding: 24px; }
.empty { text-align: center; padding: 80px 20px; color: var(--fg3); }
.empty h3 { font-size: 18px; margin-bottom: 8px; color: var(--fg2); }
.skill-card { background: var(--bg2); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px; margin-bottom: 14px; box-shadow: var(--card-shadow); transition: box-shadow 0.2s; }
.skill-card:hover { box-shadow: 0 4px 16px rgba(74,44,42,0.1); }
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
.modal-overlay { position: fixed; inset: 0; background: rgba(26,15,14,0.6); display: none; z-index: 100; align-items: center; justify-content: center; backdrop-filter: blur(2px); }
.modal-overlay.open { display: flex; }
.modal { background: var(--bg2); border-radius: 16px; width: 94%; max-width: 1100px; max-height: 90vh; display: flex; flex-direction: column; box-shadow: 0 12px 48px rgba(74,44,42,0.2); border: 1px solid var(--border); }
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
.md-content hr { border: none; border-top: 1px solid var(--border); margin: 20px 0; }
.compare-controls { display: flex; gap: 12px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }
.compare-controls label { font-size: 13px; color: var(--fg2); font-weight: 500; }
.compare-controls select { padding: 6px 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg); color: var(--fg); font-size: 13px; }
.compare-mode { display: flex; gap: 4px; }
.compare-mode button { padding: 5px 12px; border: 1px solid var(--border); background: var(--bg); color: var(--fg2); cursor: pointer; font-size: 12px; }
.compare-mode button:first-child { border-radius: 6px 0 0 6px; }
.compare-mode button:last-child { border-radius: 0 6px 6px 0; }
.compare-mode button.active { background: var(--accent); color: white; border-color: var(--accent); }
.diff-side { display: flex; border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
.diff-pane { flex: 1; overflow-x: auto; }
.diff-pane-header { padding: 8px 14px; background: var(--bg3); font-size: 12px; font-weight: 600; color: var(--accent-dark); border-bottom: 1px solid var(--border); }
.diff-pane:first-child { border-right: 1px solid var(--border); }
.diff-pane-line { padding: 1px 14px; font-family: 'Cascadia Code', 'SF Mono', Consolas, monospace; font-size: 12px; white-space: pre-wrap; word-break: break-all; min-height: 20px; display: flex; }
.diff-pane-line .ln { color: var(--fg3); min-width: 32px; text-align: right; padding-right: 10px; user-select: none; opacity: 0.5; }
.diff-pane-line.diff-add { background: var(--diff-add); color: var(--diff-add-fg); }
.diff-pane-line.diff-rm { background: var(--diff-rm); color: var(--diff-rm-fg); }
.diff-pane-line.diff-empty { background: var(--bg3); opacity: 0.3; }
.diff-view { margin-top: 12px; border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
.diff-header { padding: 10px 14px; background: var(--bg3); font-size: 13px; font-weight: 600; color: var(--accent-dark); border-bottom: 1px solid var(--border); }
.diff-line { padding: 3px 14px; font-family: 'Cascadia Code', 'SF Mono', Consolas, monospace; font-size: 12px; white-space: pre-wrap; word-break: break-all; }
.diff-add { background: var(--diff-add); color: var(--diff-add-fg); }
.diff-rm { background: var(--diff-rm); color: var(--diff-rm-fg); }
.diff-ctx { color: var(--fg3); }
.timeline { display: flex; flex-direction: column; gap: 2px; }
.timeline-item { display: flex; align-items: stretch; gap: 14px; cursor: pointer; padding: 12px 14px; border-radius: 8px; transition: background 0.15s; }
.timeline-item:hover { background: var(--bg3); }
.timeline-dot-col { display: flex; flex-direction: column; align-items: center; width: 20px; }
.timeline-dot { width: 12px; height: 12px; border-radius: 50%; background: var(--border); flex-shrink: 0; margin-top: 4px; }
.timeline-dot.current { background: var(--accent); box-shadow: 0 0 0 3px rgba(192,57,43,0.25); }
.timeline-line { flex: 1; width: 2px; background: var(--border); margin-top: 4px; }
.timeline-info { flex: 1; }
.timeline-version { font-size: 14px; font-weight: 600; color: var(--accent-dark); }
.timeline-label { font-size: 12px; color: var(--fg3); margin-top: 2px; }
.timeline-item:last-child .timeline-line { display: none; }
.sidebar-overlay { display: none; }
@media (max-width: 640px) {
  body { flex-direction: column; }
  .hamburger { display: flex; }
  .sidebar { position: fixed; top: 0; left: -100%; width: 85%; max-width: 320px; height: 100vh; z-index: 200; border-right: 1px solid var(--border); transition: left 0.25s ease; box-shadow: none; }
  .sidebar.mobile-open { left: 0; box-shadow: 4px 0 24px rgba(0,0,0,0.15); }
  .sidebar-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 199; }
  .sidebar-overlay.visible { display: block; }
  .content { padding: 16px; }
  .modal { width: 96%; max-height: 90vh; border-radius: 12px; }
  .topbar { gap: 8px; padding: 10px 14px; }
  .skill-meta { flex-direction: column; gap: 4px; }
  .diff-side { flex-direction: column; }
  .diff-pane:first-child { border-right: none; border-bottom: 1px solid var(--border); }
}
</style>
</head>
<body>
<div id="loading" style="position:fixed;inset:0;background:var(--bg);z-index:999;display:flex;align-items:center;justify-content:center;flex-direction:column">
  <div style="font-size:20px;font-weight:600;color:var(--accent-dark);margin-bottom:8px"><span style="color:var(--accent)">/</span>skillforge</div>
  <div style="font-size:13px;color:var(--fg3);margin-bottom:20px">Loading dashboard...</div>
  <div style="width:200px;height:3px;background:var(--border);border-radius:2px;overflow:hidden"><div style="width:40%;height:100%;background:var(--accent);border-radius:2px;animation:loadSlide 1.2s ease-in-out infinite"></div></div>
  <style>@keyframes loadSlide{0%{transform:translateX(-100%)}100%{transform:translateX(350%)}}</style>
</div>
<div class="sidebar">
  <div class="sidebar-header">
    <div class="sidebar-brand">
      <h2><span>/</span>skillforge</h2>
      <button class="theme-btn" onclick="toggleTheme()" title="Toggle theme">&#9681;</button>
    </div>
  </div>
  <div class="project-list" id="projectList"></div>
  <div class="sidebar-footer" id="generated"></div>
</div>
<div class="main">
  <div class="sidebar-overlay" id="sidebarOverlay" onclick="closeMobileMenu()"></div>
  <div class="topbar">
    <button class="hamburger" onclick="toggleMobileMenu()" title="Projects">&#9776;</button>
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
let currentProject = null, searchQuery = '', modalSkill = null, diffMode = 'side';
let timelinePageSize = 10, timelineShown = 10;

function init() {
  const theme = localStorage.getItem('sf-theme') || 'light';
  document.documentElement.setAttribute('data-theme', theme);
  document.getElementById('generated').textContent = 'Generated: ' + new Date(DATA.generated).toLocaleString('en-GB', {day:'numeric',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'});
  renderProjects(); renderSkills();
  document.getElementById('search').addEventListener('input', e => { searchQuery = e.target.value.toLowerCase(); renderSkills(); });
}
function toggleTheme() { const c = document.documentElement.getAttribute('data-theme'); const n = c === 'dark' ? 'light' : 'dark'; document.documentElement.setAttribute('data-theme', n); localStorage.setItem('sf-theme', n); }
function toggleMobileMenu() { document.querySelector('.sidebar').classList.toggle('mobile-open'); document.getElementById('sidebarOverlay').classList.toggle('visible'); }
function closeMobileMenu() { document.querySelector('.sidebar').classList.remove('mobile-open'); document.getElementById('sidebarOverlay').classList.remove('visible'); }

function renderProjects() {
  const el = document.getElementById('projectList');
  const totalSkills = DATA.projects.reduce((a, p) => a + p.skills.length, 0);
  let html = `<div class="project-item ${currentProject === null ? 'active' : ''}" onclick="selectProject(null)"><span>All Projects</span><span class="count">${totalSkills}</span></div>`;
  for (let i = 0; i < DATA.projects.length; i++) {
    const p = DATA.projects[i];
    const sel = currentProject === i ? 'active' : '';
    html += `<div class="project-item ${sel}" onclick="selectProject(${i})"><div class="project-info"><div class="project-name">${esc(p.name)}</div><div class="project-path" title="${esc(p.path)}">${esc(p.path)}</div></div><span class="count">${p.skills.length}</span></div>`;
  }
  el.innerHTML = html;
}
function selectProject(idx) { currentProject = idx; closeMobileMenu(); renderProjects(); renderSkills(); }

function getFilteredSkills() {
  let skills = [];
  for (let i = 0; i < DATA.projects.length; i++) {
    if (currentProject !== null && currentProject !== i) continue;
    for (const s of DATA.projects[i].skills) skills.push({...s, projectName: DATA.projects[i].name, projectIdx: i});
  }
  if (searchQuery) skills = skills.filter(s => s.name.toLowerCase().includes(searchQuery) || s.description.toLowerCase().includes(searchQuery) || s.id.toLowerCase().includes(searchQuery) || (s.tags||[]).some(t => t.toLowerCase().includes(searchQuery)));
  return skills;
}

function renderSkills() {
  const skills = getFilteredSkills(), el = document.getElementById('content');
  if (!skills.length) { el.innerHTML = '<div class="empty"><h3>No skills found</h3><p>Run /skillforge-launch to generate skills.</p></div>'; return; }
  el.innerHTML = skills.map((s, i) => {
    const tags = (s.tags||[]).map(t => `<span class="tag">${esc(t)}</span>`).join('');
    const cat = s.category ? `<span class="tag" style="background:var(--accent);color:white;border:none">${esc(s.category)}</span>` : '';
    const proj = currentProject === null ? `<span>${esc(s.projectName)}</span>` : '';
    return `<div class="skill-card" id="card-${i}"><div class="skill-header"><span class="skill-name">${esc(s.name)}</span><span class="skill-version">v${s.current_version}</span></div>${s.description ? `<div class="skill-desc">${esc(s.description)}</div>` : ''}<div class="skill-meta">${proj}<span>Created: ${fmtDate(s.created)}</span><span>Updated: ${fmtDate(s.updated)}</span></div><div class="skill-tags">${cat}${tags}</div><div class="skill-actions"><button class="btn btn-primary" onclick="viewSkill(${i})">View</button></div></div>`;
  }).join('');
}

function viewSkill(idx) {
  const skills = getFilteredSkills(); modalSkill = skills[idx]; const s = modalSkill;
  const current = s.versions.find(v => v.current); if (!current) return;
  document.getElementById('modalTitle').innerHTML = '<span style="color:var(--accent);font-size:24px;font-weight:700;margin-right:2px">/</span>' + esc(s.name);
  const hasManyVersions = s.versions.filter(v => !v.capped).length > 1;
  let tabs = `<div class="modal-tab active" onclick="switchTab('content')">Content (v${s.current_version})</div>`;
  if (hasManyVersions) { tabs += `<div class="modal-tab" onclick="switchTab('history')">History</div><div class="modal-tab" onclick="switchTab('compare')">Compare</div>`; }
  document.getElementById('modalTabs').innerHTML = tabs;
  document.getElementById('tabContent').className = 'tab-content active md-content';
  const vh = (s.version_history||[]).find(h => h.version === current.version);
  const vInfo = `<div style="font-size:12px;color:var(--fg3);margin-bottom:16px;padding-bottom:10px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center"><span>Version ${current.version}${vh ? ' &middot; Created ' + fmtDate(vh.created_at) : ''} &middot; ${esc(s.description||'')}</span><button class="btn" onclick="copyCurrentSkill(this)" style="font-size:13px;font-weight:500;padding:5px 14px;flex-shrink:0;margin-left:12px">Copy skill content</button></div>`;
  document.getElementById('tabContent').innerHTML = vInfo + renderMd(current.content);
  if (hasManyVersions) { renderTimeline(); renderCompare(); }
  document.getElementById('tabHistory').className = 'tab-content';
  document.getElementById('tabCompare').className = 'tab-content';
  document.getElementById('modal').classList.add('open');
}
function switchTab(name) { document.querySelectorAll('.modal-tab').forEach(t => t.classList.remove('active')); document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active')); event.target.classList.add('active'); const map = {content:'tabContent',history:'tabHistory',compare:'tabCompare'}; const el = document.getElementById(map[name]); if (el) { el.classList.add('active'); if (name==='history') el.classList.add('md-content'); } }
function closeModal() { document.getElementById('modal').classList.remove('open'); modalSkill = null; }
function copyCurrentSkill(btn) { if (!modalSkill) return; const c = modalSkill.versions.find(v => v.current); if (!c) return; navigator.clipboard.writeText(c.content).then(() => { const o = btn.textContent; btn.textContent = 'Copied!'; setTimeout(() => btn.textContent = o, 1000); }); }
function showVersionInModal(vIdx) { const v = modalSkill.versions[vIdx]; const vh = (modalSkill.version_history||[]).find(h => h.version === v.version); const info = `<div style="font-size:12px;color:var(--fg3);margin-bottom:16px;padding-bottom:10px;border-bottom:1px solid var(--border)">Version ${v.version}${vh ? ' &middot; Created ' + fmtDate(vh.created_at) : ''}</div>`; document.getElementById('tabContent').innerHTML = info + renderMd(v.content); document.querySelectorAll('.modal-tab').forEach(t => t.classList.remove('active')); document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active')); const ct = document.querySelector('.modal-tab'); ct.classList.add('active'); ct.textContent = 'Content (v' + v.version + ')'; document.getElementById('tabContent').classList.add('active'); }

function renderTimeline() {
  const s = modalSkill; timelineShown = timelinePageSize;
  const realVersions = s.versions.filter(v => !v.capped);
  const cappedEntry = s.versions.find(v => v.capped);
  let html = '';
  if (cappedEntry) html += `<div style="padding:10px 14px;font-size:12px;color:var(--fg3);background:var(--bg3);border-radius:8px;margin-bottom:10px;">Showing last ${realVersions.length} versions. ${cappedEntry.hidden_count} older versions archived on disk.</div>`;
  html += '<div class="timeline" id="timelineList">';
  const items = [];
  for (let i = realVersions.length - 1; i >= 0; i--) {
    const v = realVersions[i], origIdx = s.versions.indexOf(v), isCurrent = v.current ? 'current' : '';
    const vh = (s.version_history||[]).find(h => h.version === v.version);
    const dateStr = vh ? fmtDate(vh.created_at) : '';
    items.push(`<div class="timeline-item" onclick="showVersionInModal(${origIdx})"><div class="timeline-dot-col"><div class="timeline-dot ${isCurrent}"></div><div class="timeline-line"></div></div><div class="timeline-info"><div class="timeline-version">Version ${v.version} ${v.current ? '(current)' : ''}</div><div class="timeline-label">${dateStr ? 'Created ' + dateStr : (v.current ? 'Latest' : 'Archived')}</div></div></div>`);
  }
  html += items.slice(0, timelineShown).join('') + '</div>';
  if (items.length > timelineShown) html += `<button class="btn" style="margin-top:10px;width:100%" onclick="showMoreTimeline()">Show more (${items.length - timelineShown} remaining)</button>`;
  document.getElementById('tabHistory').innerHTML = html; window._timelineItems = items;
}
function showMoreTimeline() { timelineShown += timelinePageSize; const list = document.getElementById('timelineList'), items = window._timelineItems; list.innerHTML = items.slice(0, timelineShown).join(''); const btn = list.parentElement.querySelector('button'); if (timelineShown >= items.length) { if (btn) btn.remove(); } else if (btn) { btn.textContent = `Show more (${items.length - timelineShown} remaining)`; } }

function renderCompare() {
  const s = modalSkill, vers = s.versions.filter(v => !v.capped);
  let optionsA = '', optionsB = '';
  for (let i = 0; i < vers.length; i++) { const origIdx = s.versions.indexOf(vers[i]); const sel = i === Math.max(0, vers.length - 2) ? 'selected' : ''; optionsA += `<option value="${origIdx}" ${sel}>v${vers[i].version}${vers[i].current ? ' (current)' : ''}</option>`; }
  for (let i = 0; i < vers.length; i++) { const origIdx = s.versions.indexOf(vers[i]); const sel = i === vers.length - 1 ? 'selected' : ''; optionsB += `<option value="${origIdx}" ${sel}>v${vers[i].version}${vers[i].current ? ' (current)' : ''}</option>`; }
  document.getElementById('tabCompare').innerHTML = `<div class="compare-controls"><label>From</label><select id="diffA" onchange="updateDiff()">${optionsA}</select><button class="btn" onclick="swapDiff()" title="Swap" style="padding:5px 10px;font-size:14px">&#8646;</button><label>To</label><select id="diffB" onchange="updateDiff()">${optionsB}</select><div class="compare-mode"><button class="${diffMode==='side'?'active':''}" onclick="setDiffMode('side')">Side by side</button><button class="${diffMode==='inline'?'active':''}" onclick="setDiffMode('inline')">Inline</button></div></div><div id="diffOutput"></div>`;
  updateDiff();
}
function swapDiff() { const a = document.getElementById('diffA'), b = document.getElementById('diffB'), t = a.value; a.value = b.value; b.value = t; updateDiff(); }
function setDiffMode(m) { diffMode = m; document.querySelectorAll('.compare-mode button').forEach(b => b.classList.remove('active')); event.target.classList.add('active'); updateDiff(); }
function updateDiff() { const aI = parseInt(document.getElementById('diffA').value), bI = parseInt(document.getElementById('diffB').value); const a = modalSkill.versions[aI].content||'', b = modalSkill.versions[bI].content||''; const d = lineDiff(a,b), vA = modalSkill.versions[aI].version, vB = modalSkill.versions[bI].version; document.getElementById('diffOutput').innerHTML = diffMode === 'side' ? renderSideDiff(d,vA,vB) : renderInlineDiff(d,vA,vB); }
function renderSideDiff(diff,vA,vB) { let l=[],r=[],lnA=1,lnB=1; for (const d of diff) { if(d.type==='ctx'){l.push({ln:lnA++,text:d.text,cls:''});r.push({ln:lnB++,text:d.text,cls:''});} else if(d.type==='rm'){l.push({ln:lnA++,text:d.text,cls:'diff-rm'});r.push({ln:'',text:'',cls:'diff-empty'});} else{l.push({ln:'',text:'',cls:'diff-empty'});r.push({ln:lnB++,text:d.text,cls:'diff-add'});} } const rp=lines=>lines.map(l=>`<div class="diff-pane-line ${l.cls}"><span class="ln">${l.ln}</span><span>${esc(l.text)}</span></div>`).join(''); return `<div class="diff-side"><div class="diff-pane"><div class="diff-pane-header">v${vA}</div>${rp(l)}</div><div class="diff-pane"><div class="diff-pane-header">v${vB}</div>${rp(r)}</div></div>`; }
function renderInlineDiff(diff,vA,vB) { let h=`<div class="diff-view"><div class="diff-header">v${vA} → v${vB}</div>`; for(const d of diff){if(d.type==='add')h+=`<div class="diff-line diff-add">+ ${esc(d.text)}</div>`;else if(d.type==='rm')h+=`<div class="diff-line diff-rm">- ${esc(d.text)}</div>`;else h+=`<div class="diff-line diff-ctx">  ${esc(d.text)}</div>`;} return h+'</div>'; }

function renderMd(text) { if(!text)return''; const lines=text.split('\n'); let html='',inCode=false,codeBuf=[],inList=false,listType=''; function flushList(){if(inList){html+=listType==='ol'?'</ol>':'</ul>';inList=false;}} for(let i=0;i<lines.length;i++){const line=lines[i]; if(line.startsWith('```')){if(inCode){html+='<pre><code>'+esc(codeBuf.join('\n'))+'</code></pre>';codeBuf=[];inCode=false;}else{flushList();inCode=true;}continue;} if(inCode){codeBuf.push(line);continue;} if(line.startsWith('---')&&line.trim()==='---'){if(i<3)continue;flushList();html+='<hr>';continue;} if(/^#{1,6}\s/.test(line)){flushList();const lvl=line.match(/^(#+)/)[1].length;html+=`<h${lvl}>${inline(line.replace(/^#+\s*/,''))}</h${lvl}>`;continue;} if(/^[\-\*]\s/.test(line)){if(!inList||listType!=='ul'){flushList();html+='<ul>';inList=true;listType='ul';}html+=`<li>${inline(line.replace(/^[\-\*]\s*/,''))}</li>`;continue;} if(/^\d+\.\s/.test(line)){if(!inList||listType!=='ol'){flushList();html+='<ol>';inList=true;listType='ol';}html+=`<li>${inline(line.replace(/^\d+\.\s*/,''))}</li>`;continue;} flushList();if(line.trim()==='')continue;if(i<5&&/^[a-z_]+:/.test(line))continue;html+=`<p>${inline(line)}</p>`;} flushList();if(inCode)html+='<pre><code>'+esc(codeBuf.join('\n'))+'</code></pre>';return html; }
function inline(t){return t.replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>').replace(/\*([^*]+)\*/g,'<em>$1</em>').replace(/\[([^\]]+)\]\(([^)]+)\)/g,(m,l,u)=>{if(/^(javascript|data|vbscript):/i.test(u))return esc(l);return`<a href="${u}" target="_blank">${l}</a>`;});}

function lineDiff(a,b){const la=a.split('\n'),lb=b.split('\n'),n=la.length,m=lb.length,max=n+m,v=new Array(2*max+1).fill(0),trace=[];for(let d=0;d<=max;d++){trace.push([...v]);for(let k=-d;k<=d;k+=2){let x;if(k===-d||(k!==d&&v[k-1+max]<v[k+1+max]))x=v[k+1+max];else x=v[k-1+max]+1;let y=x-k;while(x<n&&y<m&&la[x]===lb[y]){x++;y++;}v[k+max]=x;if(x>=n&&y>=m)return buildDiff(la,lb,trace,d,max);}}return la.map(t=>({type:'rm',text:t})).concat(lb.map(t=>({type:'add',text:t})));}
function buildDiff(la,lb,trace,D,max){let x=la.length,y=lb.length;const edits=[];for(let d=D;d>0;d--){const v=trace[d-1],k=x-y;let pK;if(k===-d||(k!==d&&v[k-1+max]<v[k+1+max]))pK=k+1;else pK=k-1;const pX=v[pK+max],pY=pX-pK;while(x>pX&&y>pY){x--;y--;edits.unshift({type:'ctx',text:la[x]});}if(x>pX){x--;edits.unshift({type:'rm',text:la[x]});}else if(y>pY){y--;edits.unshift({type:'add',text:lb[y]});}}while(x>0&&y>0){x--;y--;edits.unshift({type:'ctx',text:la[x]});}return edits;}

function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function fmtDate(s){if(!s)return'—';try{return new Date(s).toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'});}catch(e){return s;}}
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal();});

function enableDragScroll(el){let isDown=false,startY,scrollTop;el.addEventListener('mousedown',e=>{if(e.target.closest('button,a,input,select'))return;isDown=true;el.classList.add('dragging');startY=e.pageY-el.offsetTop;scrollTop=el.scrollTop;});el.addEventListener('mouseleave',()=>{isDown=false;el.classList.remove('dragging');});el.addEventListener('mouseup',()=>{isDown=false;el.classList.remove('dragging');});el.addEventListener('mousemove',e=>{if(!isDown)return;e.preventDefault();el.scrollTop=scrollTop-(e.pageY-el.offsetTop-startY);});}
document.querySelectorAll('.project-list,.content').forEach(enableDragScroll);

init();
document.getElementById('loading').style.display='none';
</script>
</body>
</html>"""


def generate(no_open: bool = False) -> dict:
    data = _collect_data()
    data_json = json.dumps(data, ensure_ascii=False)
    html = _HTML_TEMPLATE.replace("__DATA__", data_json)

    out_dir = skillforge_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "dashboard.html"
    tmp_path = out_path.with_suffix(".tmp")
    tmp_path.write_text(html, encoding="utf-8")
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
