black:
	isort .
	black .

lint:
	black --diff --check .
	isort -c --diff .
	flake8
	@echo "🙊 Code 🙈 LGTM 🙉 !"

deployment-checks:
	PULP_DEPLOYMENT="dev" APP_KEY="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef" ./manage.py check --deploy --fail-level WARNING
	@echo "✅ Dev deployment checks passed 🚀 !"
	PULP_DEPLOYMENT="prod" APP_KEY="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef" ./manage.py check --deploy --fail-level WARNING
	@echo "✅ Prod deployment checks passed 🚀 !"

.PHONY: black lint deployment-checks
