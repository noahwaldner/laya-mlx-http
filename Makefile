.PHONY: setup test check build check-versions bump serve stop restart logs clean

setup:            ## create .venv + install python and node dev deps
	@[ -d .venv ] || uv venv
	uv pip install -e './python[dev]' --python .venv/bin/python
	cd ai-provider && npm install

test:             ## python + node test suites
	.venv/bin/python -m pytest python/tests
	cd ai-provider && npm test && npm run type-check

check: test check-versions

build:            ## python sdist/wheel + npm dist (pack preview)
	rm -rf dist
	uv build --out-dir dist python
	cd ai-provider && npm run build && npm pack --dry-run

check-versions:   ## all four version strings agree (TAG=vX.Y.Z to compare a tag)
	python3 scripts/versions.py check $(TAG)

bump:             ## write VERSION into all four files: make bump VERSION=0.2.0
	python3 scripts/versions.py set $(VERSION)

serve:
	./ctl.sh start

stop:
	./ctl.sh stop

restart:
	./ctl.sh restart

logs:
	./ctl.sh logs

clean:
	rm -rf dist python/dist ai-provider/dist
