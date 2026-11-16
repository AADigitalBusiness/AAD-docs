#!/usr/bin/env python3
"""Render the documentation files of a git repo as one self-contained HTML page.
Usage: python3 repo_canvas.py <repo_root> <out.html> [--title "Name"] [--pending-regex REGEX]
Files: every git-tracked .md .mdx .yml .yaml .csv .json .py under docs/ folders, plus root *.md.
--pending-regex: files whose '**Status:**' line matches it are highlighted as pending (warning color)."""
import os, re, csv, io, html, subprocess, posixpath, sys, argparse
from markdown_it import MarkdownIt

ap = argparse.ArgumentParser()
ap.add_argument('root'); ap.add_argument('out')
ap.add_argument('--title', default='Repository docs')
ap.add_argument('--pending-regex', default=r'^(Proposed|Draft|Pending)')
ap.add_argument('--approvals', action='store_true', help='add Approve / Request changes controls to pending decisions (needs the db and user capabilities)')
a = ap.parse_args()
R = a.root
EXT = ('.md', '.mdx', '.yml', '.yaml', '.csv', '.json', '.py')
tracked = subprocess.check_output(['git', 'ls-files'], cwd=R, text=True).split()
files = [f for f in tracked if f.endswith(EXT) and ('/docs/' in '/' + f or '/' not in f and f.endswith('.md'))]
ids = {f: 'f-' + re.sub(r'[^a-z0-9]+', '-', f.lower()).strip('-') for f in files}

md = MarkdownIt('commonmark').enable('table')
def fence(self, tokens, idx, options, env):
    t = tokens[idx]
    if t.info.strip() == 'mermaid':
        return '<pre class="mermaid">%s</pre>\n' % html.escape(t.content)
    return '<pre class="code"><code>%s</code></pre>\n' % html.escape(t.content)
md.add_render_rule('fence', fence)

def fix_links(tokens, cur):
    for t in tokens:
        if t.children: fix_links(t.children, cur)
        if t.type != 'link_open': continue
        h = t.attrGet('href') or ''
        if h.startswith(('http://', 'https://')):
            t.attrSet('target', '_blank'); t.attrSet('rel', 'noopener'); continue
        if h.startswith('mailto:'): continue
        path = h.split('#')[0]
        if not path: continue
        tgt = posixpath.normpath(posixpath.join(posixpath.dirname(cur), path))
        if tgt in ids: t.attrSet('href', '#' + ids[tgt])
        else:
            c = [f for f in files if f.startswith(tgt.rstrip('/') + '/')]
            t.attrSet('href', '#' + ids[c[0]] if c else '#')

def render(f):
    s = open(os.path.join(R, f), encoding='utf-8').read()
    ext = f.rsplit('.', 1)[-1]
    if ext == 'md':
        badge = ''
        m = re.match(r'---\n(.*?)\n---\n', s, re.S)
        if m:
            badge = '<p class="badge">%s</p>' % html.escape(m.group(1).replace('\n', ' · ')); s = s[m.end():]
        toks = md.parse(s); fix_links(toks, f)
        return badge + md.renderer.render(toks, md.options, {})
    if ext == 'csv':
        rows = list(csv.reader(io.StringIO(s)))
        h = '<div class="tw"><table><thead><tr>' + ''.join('<th>%s</th>' % html.escape(c) for c in rows[0]) + '</tr></thead><tbody>'
        for r in rows[1:]: h += '<tr>' + ''.join('<td>%s</td>' % html.escape(c) for c in r) + '</tr>'
        return '<p class="badge">Table</p>' + h + '</tbody></table></div>'
    note = {'mdx': 'MDX source: the docs app renders its tags as components', 'yml': 'YAML data file', 'yaml': 'YAML data file',
            'json': 'JSON data file', 'py': 'Python module'}[ext]
    return '<p class="badge">%s</p><pre class="code"><code>%s</code></pre>' % (note, html.escape(s))

def status_of(f):
    m = re.search(r'^\*\*Status:\*\* (.*)', open(os.path.join(R, f), encoding='utf-8').read(), re.M)
    return m.group(1) if m else None
def title_of(f):
    m = re.search(r'^# (.*)', open(os.path.join(R, f), encoding='utf-8').read(), re.M)
    return m.group(1) if m else os.path.basename(f)

pend = {}
for f in files:
    if f.endswith(('.md', '.mdx')):
        st = status_of(f)
        if st and re.search(a.pending_regex, st): pend[f] = st

def group(f):
    d = posixpath.dirname(f)
    return d + '/' if d else 'Root'
groups = {}
for f in files: groups.setdefault(group(f), []).append(f)
nav = body = ''
for g in sorted(groups, key=lambda x: (x != 'Root', x)):
    nav += '<div class="g"><h3>%s</h3>' % html.escape(g)
    for f in groups[g]:
        nav += '<a href="#%s"%s>%s</a>' % (ids[f], ' class="warn"' if f in pend else '', html.escape(posixpath.basename(f)))
        r = render(f)
        if f in pend:
            r = re.sub(r'<p><strong>Status:</strong>(.*?)</p>', r'<p class="warnbox"><strong>Pending · Status:</strong>\1</p>', r, count=1)
        if a.approvals and f in pend:
            m = re.search(r'/(\d{4})-[^/]*$', f)
            if m:
                r = re.sub(r'(</p>)', r'\1<div class="appr" data-id="%s" data-title="%s"></div>' % (m.group(1), html.escape(title_of(f), quote=True)), r, count=1) if 'warnbox' not in r else re.sub(r'(<p class="warnbox">.*?</p>)', r'\1<div class="appr" data-id="%s" data-title="%s"></div>' % (m.group(1), html.escape(title_of(f), quote=True)), r, count=1)
        body += '<section id="%s"%s><div class="path">%s</div>%s</section>\n' % (ids[f], ' class="pend"' if f in pend else '', html.escape(f), r)
    nav += '</div>'
if pend:
    def dec(f):
        m = re.search(r'/(\d{4})-[^/]*$', f)
        return ' data-decision="%s"' % m.group(1) if a.approvals and m else ''
    li = ''.join('<li%s><a href="#%s">%s</a> <span>%s</span></li>' % (dec(f), ids[f], html.escape(title_of(f)), html.escape(st[:60])) for f, st in pend.items())
    body = '<section id="pending" class="pend"><div class="path">Needs the owner</div><h1>Pending decisions</h1><ul class="pl">%s</ul></section>\n' % li + body
    nav = '<div class="g"><h3>Needs the owner</h3><a class="warn" href="#pending">Pending (%d)</a></div>' % len(pend) + nav

here = os.path.dirname(os.path.abspath(__file__))
tpl = open(os.path.join(here, 'repo_canvas.template.html'), encoding='utf-8').read()
out = (tpl.replace('%%TITLE%%', html.escape(a.title)).replace('%%NAV%%', nav)
          .replace('%%BODY%%', body).replace('%%COUNT%%', str(len(files))))
script = open(os.path.join(here, 'approvals.js.html'), encoding='utf-8').read() if a.approvals else ''
out = out.replace('%%SCRIPT%%', script)
open(a.out, 'w', encoding='utf-8').write(out)
print('files', len(files), 'pending', len(pend), 'bytes', len(out))
