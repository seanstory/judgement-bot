.PHONY: install clean run ingest

install:
	pip install -r requirements.txt

clean:
	rm -rf output/

run:
	python3 parse_rulebook.py

ingest:
	python3 ingest.py
