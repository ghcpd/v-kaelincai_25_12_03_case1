#!/usr/bin/env bash
# Run all tests and collect results
mkdir -p results
python -m pytest -q --disable-warnings --maxfail=1 --junitxml=results/results_post.xml
# Summarize
python - <<'PY'
import xml.etree.ElementTree as ET
try:
    tree = ET.parse('results/results_post.xml')
    root = tree.getroot()
    tests = int(root.attrib.get('tests','0'))
    failures = int(root.attrib.get('failures','0'))
    print(f"tests={tests} failures={failures}")
except Exception as e:
    print('no results')
PY
