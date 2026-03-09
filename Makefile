.PHONY: format
format:
	.ci/sync_requirements.py --fix
	ruff format
	ruff check --fix

.PHONY: lint
lint:
	.ci/sync_requirements.py
	ruff format --check --diff
	ruff check --diff
	@echo "🙊 Code 🙈 LGTM 🙉 !"

.PHONY: test
test:
	pytest -v
