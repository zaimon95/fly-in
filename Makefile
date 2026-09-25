VENV     = .venv
PYTHON   = $(VENV)/bin/python3
MAIN     = fly-in.py
INSTALLED = $(VENV)/.installed

.PHONY: install run debug lint lint-strict clean fclean

install: $(INSTALLED)

# Real file target, created only once every package is installed: the
# install is redone if it never completed, or if requirements.txt is
# newer than the last successful install.
$(INSTALLED): requirements.txt
	python3 -m venv $(VENV)
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt
	touch $(INSTALLED)

run: $(INSTALLED)
	$(PYTHON) $(MAIN) $(CONFIG)

debug: $(INSTALLED)
	$(PYTHON) -m pdb $(MAIN) $(CONFIG)

clean:
	find . -type d -name __pycache__ -not -path "./$(VENV)/*" \
		-exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -not -path "./$(VENV)/*" -delete
	rm -rf dist/ build/ *.egg-info/

fclean: clean
	rm -rf $(VENV)

lint: $(INSTALLED)
	$(PYTHON) -m flake8 . --exclude $(VENV)
	$(PYTHON) -m mypy . \
		--exclude $(VENV) \
		--warn-return-any \
		--warn-unused-ignores \
		--ignore-missing-imports \
		--disallow-untyped-defs \
		--check-untyped-defs

lint-strict: $(INSTALLED)
	$(PYTHON) -m flake8 . --exclude $(VENV)
	$(PYTHON) -m mypy . --exclude $(VENV) --strict