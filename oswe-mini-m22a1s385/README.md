oswe-mini-m22a1s385 — Greenfield scheduling replacement POC

How to run (Windows PowerShell):

# Create venv and install
python -m venv .venv; .\.venv\Scripts\Activate; python -m pip install -r requirements.txt

# Run tests
.\.venv\Scripts\pytest -q

Notes:
- This is a proof-of-concept repository scaffolding and a starting point for a greenfield replacement. Tests exercise crash points, idempotency, retries, and outbox semantics.
- See docs/*.md for design rationale and migration guidance.
