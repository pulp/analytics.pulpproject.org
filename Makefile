black:
	isort .
	black .

lint:
	black --diff --check .
	isort -c --diff .
	flake8
	@echo "🙊 Code 🙈 LGTM 🙉 !"

.PHONY: black lint
