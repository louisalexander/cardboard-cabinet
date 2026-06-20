.PHONY: help install dev dev-verbose test test-unit test-integration test-slow test-file test-coverage \
        lint format check \
        test-js db-reset export deploy \
        ci-install ci-check ci-test \
        docker-build docker-run \
        clean clean-all

# ── Variables ─────────────────────────────────────────────────────────────────

VENV    := .venv
PYTHON  := $(VENV)/bin/python
PIP     := $(VENV)/bin/pip
PYTEST  := $(VENV)/bin/pytest
UVICORN := $(VENV)/bin/uvicorn
BLACK   := $(VENV)/bin/black
FLAKE8  := $(VENV)/bin/flake8

IMAGE   := cardboard-cabinet
PORT    := 8000
DB_PATH := data/games.db

# Sentinel file touched after a successful pip install. Using activate as the
# sentinel is unreliable because pip doesn't update it when packages change.
INSTALLED := $(VENV)/.installed

# ── Help (default target) ─────────────────────────────────────────────────────

help:
	@echo "Cardboard Cabinet — available targets"
	@echo ""
	@echo "  Setup"
	@echo "    install          Create .venv and install all dependencies"
	@echo ""
	@echo "  Development"
	@echo "    dev              Run uvicorn with --reload on PORT=$(PORT)"
	@echo "    dev-verbose      Run uvicorn with debug logging and --reload"
	@echo ""
	@echo "  Testing"
	@echo "    test             Run the full test suite"
	@echo "    test-unit        Run only tests marked 'unit'"
	@echo "    test-integration Run only tests marked 'integration'"
	@echo "    test-slow        Run only tests marked 'slow'"
	@echo "    test-file FILE=  Run a single file or test node, e.g. FILE=tests/unit/test_db_storage.py"
	@echo "    test-coverage    Run tests and produce an HTML coverage report"
	@echo ""
	@echo "  Code quality"
	@echo "    format           Auto-format app/ and tests/ with black"
	@echo "    lint             Lint app/ and tests/ with flake8"
	@echo "    check            Dry-run format check + lint (CI-friendly, no writes)"
	@echo ""
	@echo "  Database"
	@echo "    db-reset         Delete data/games.db and recreate an empty schema"
	@echo ""
	@echo "  Docker"
	@echo "    docker-build     Build the Docker image tagged '$(IMAGE)'"
	@echo "    docker-run       Run the image on port $(PORT) (falls back to .env)"
	@echo "                     Override creds: make docker-run BGG_USERNAME=x BGG_PASSWORD=y"
	@echo ""
	@echo "  Cleanup"
	@echo "    clean            Remove .venv, caches, and compiled bytecode"
	@echo "    clean-all        Same as clean, plus deletes data/games.db"
	@echo ""
	@echo "  CI (tools expected on PATH, not from .venv)"
	@echo "    ci-install       pip install runtime + dev dependencies"
	@echo "    ci-check         black --check + flake8"
	@echo "    ci-test          pytest"
	@echo ""
	@echo "Override PORT with: make dev PORT=9000"

# ── Local setup ───────────────────────────────────────────────────────────────

# The sentinel is touched only after both install passes succeed.
# Re-runs automatically when requirements.txt changes.
$(INSTALLED): requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install --quiet --upgrade pip
	$(PIP) install --quiet -r requirements.txt
	$(PIP) install --quiet black flake8 pytest-cov
	touch $(INSTALLED)

install: $(INSTALLED)

# ── Development server ────────────────────────────────────────────────────────

dev: install
	$(UVICORN) app.main:app --reload --port $(PORT)

# Full debug logging — useful when diagnosing request handling or SQL issues.
dev-verbose: install
	$(UVICORN) app.main:app --reload --port $(PORT) --log-level debug

# ── Tests ─────────────────────────────────────────────────────────────────────

test: install
	$(PYTEST)

# Client-side parity tests for frontend/data.js (Node's built-in test runner).
# Uses an explicit glob — the bare directory form fails on Node 23+.
test-js:
	node --test tests/js/*.test.js

test-unit: install
	$(PYTEST) -m unit

test-integration: install
	$(PYTEST) -m integration

test-slow: install
	$(PYTEST) -m slow

# Usage: make test-file FILE=tests/unit/test_db_storage.py
#        make test-file FILE=tests/unit/test_db_storage.py::TestGameFiltering::test_filter_by_mechanics
test-file: install
ifndef FILE
	$(error FILE is required. Usage: make test-file FILE=tests/unit/test_foo.py)
endif
	$(PYTEST) $(FILE)

# Produces .coverage + htmlcov/index.html; open the report automatically if possible.
test-coverage: install
	$(PYTEST) --cov=app --cov-report=term-missing --cov-report=html
	@echo ""
	@echo "HTML report written to htmlcov/index.html"
	@command -v open >/dev/null 2>&1 && open htmlcov/index.html || true

# ── Code quality ──────────────────────────────────────────────────────────────

# Rewrites files in place.
format: install
	$(BLACK) app/ tests/

# Reports lint violations without modifying anything.
lint: install
	$(FLAKE8) app/ tests/

# Non-destructive: fails if formatting or lint issues exist. Suitable for pre-push hooks.
check: install
	$(BLACK) --check app/ tests/
	$(FLAKE8) app/ tests/

# ── Database ──────────────────────────────────────────────────────────────────

# Wipes the SQLite database and recreates an empty schema via the app's init path.
# The data/ directory is preserved (app/database.py creates it on import).
db-reset:
	@echo "Resetting $(DB_PATH)..."
	rm -f $(DB_PATH)
	$(PYTHON) -c "from app.database import engine; from app import db_models; db_models.Base.metadata.create_all(engine)"
	@echo "$(DB_PATH) recreated with empty schema."

# ── Static export ─────────────────────────────────────────────────────────────

# Fetch the BGG collection and write frontend/data/games.json for the static site.
export: install
	$(PYTHON) -m scripts.export_collection

# ── Deploy ────────────────────────────────────────────────────────────────────

# Deploy the static frontend to Cloudflare Pages via Wrangler.
# Requires: npx wrangler login (one-time). PROJECT defaults to cardboard-cabinet.
PROJECT ?= cardboard-cabinet
deploy:
	npx wrangler@latest pages deploy frontend --project-name=$(PROJECT)

# ── CI (tools on PATH — no .venv assumed) ────────────────────────────────────

# Installs everything into the active environment (typically a CI-managed venv).
# black, flake8, and pytest-cov are explicit here because they are not in
# requirements.txt (which is kept lean for production Docker builds).
ci-install:
	pip install --quiet -r requirements.txt
	pip install --quiet black flake8 pytest-cov

ci-check:
	black --check app/ tests/
	flake8 app/ tests/

ci-test:
	pytest

# ── Docker ────────────────────────────────────────────────────────────────────

BGG_USERNAME ?=
BGG_PASSWORD ?=

docker-build:
	docker build -t $(IMAGE) .

docker-run:
	docker run -p $(PORT):8000 \
	  $(if $(BGG_USERNAME),-e BGG_USERNAME=$(BGG_USERNAME)) \
	  $(if $(BGG_PASSWORD),-e BGG_PASSWORD='$(BGG_PASSWORD)') \
	  $(if $(and $(BGG_USERNAME),$(BGG_PASSWORD)),,--env-file .env) \
	  $(IMAGE)

# ── Cleanup ───────────────────────────────────────────────────────────────────

# Removes the venv, caches, and compiled bytecode. Leaves data/games.db intact.
clean:
	rm -rf $(VENV) .pytest_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete

# Full reset including the database. Useful when starting completely fresh.
clean-all: clean
	@echo "Deleting $(DB_PATH)..."
	rm -f $(DB_PATH)
	@echo "Done. Run 'make install' then 'make dev' to start fresh."
