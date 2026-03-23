.PHONY: install dev test test-unit test-integration lint format check build docker-build docker-run clean

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
IMAGE := cardboard-cabinet

# ── Local setup ──────────────────────────────────────────────────────────────

$(VENV)/bin/activate: requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install black flake8

install: $(VENV)/bin/activate

dev: install
	$(VENV)/bin/uvicorn app.main:app --reload

# ── Tests ─────────────────────────────────────────────────────────────────────

test: install
	$(VENV)/bin/pytest

test-unit: install
	$(VENV)/bin/pytest -m unit

test-integration: install
	$(VENV)/bin/pytest -m integration

test-file: install
	$(VENV)/bin/pytest $(FILE)

# ── Code quality ──────────────────────────────────────────────────────────────

lint: install
	$(VENV)/bin/flake8 app/ tests/

format: install
	$(VENV)/bin/black app/ tests/

check: install
	$(VENV)/bin/black --check app/ tests/
	$(VENV)/bin/flake8 app/ tests/

# ── CI (no venv assumed, tools on PATH) ───────────────────────────────────────

ci-install:
	pip install -r requirements.txt
	pip install black flake8

ci-check:
	black --check app/ tests/
	flake8 app/ tests/

ci-test:
	pytest

# ── Docker ────────────────────────────────────────────────────────────────────

docker-build:
	docker build -t $(IMAGE) .

docker-run:
	docker run -p 8000:8000 --env-file .env $(IMAGE)

# ── Misc ──────────────────────────────────────────────────────────────────────

clean:
	rm -rf $(VENV) __pycache__ .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
