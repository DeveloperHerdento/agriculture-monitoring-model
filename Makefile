# Shortcuts. No `make` on Windows? Copy the command after the `;`.
.PHONY: setup lint format test

setup:  ; python -m pip install -r requirements.txt -r requirements-dev.txt && nbstripout --install
lint:   ; ruff check . && ruff format --check .
format: ; ruff check --fix . && ruff format .
test:   ; pytest -q
