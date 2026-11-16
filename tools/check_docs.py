#!/usr/bin/env python3
"""Interim documentation check: relative links, CSV column counts, JSON and YAML syntax.
Run from anywhere: python3 tools/check_docs.py. Needs PyYAML. Replaced by `docs_check` at milestone M4."""
import csv, glob, json, os, re, sys
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
bad = 0
for f in glob.glob('**/*', recursive=True) + glob.glob('.claude/**/*', recursive=True):
    if not os.path.isfile(f) or {'node_modules', '.venv'} & set(f.split(os.sep)): continue
    if f.endswith(('.md', '.mdx')):
        for m in re.finditer(r'\]\(([^)#\s]+)(#[^)]*)?\)', open(f, encoding='utf-8').read()):
            u = m.group(1)
            if u.startswith(('http', 'mailto')): continue
            if not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(f), u))):
                print('BROKEN LINK', f, u); bad += 1
    elif f.endswith('.csv'):
        if len({len(r) for r in csv.reader(open(f, encoding='utf-8'))}) != 1:
            print('CSV COLUMNS', f); bad += 1
    elif f.endswith('.json'): json.load(open(f, encoding='utf-8'))
    elif f.endswith(('.yml', '.yaml')): yaml.safe_load(open(f, encoding='utf-8'))
print('problems:', bad)
sys.exit(1 if bad else 0)
