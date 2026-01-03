.PHONY: install clean run ingest connector clean-connectors

install:
	pip install -r requirements.txt

clean:
	rm -rf output/

run:
	python3 parse_rulebook.py

ingest:
	python3 ingest.py

connector:
	cd connector && ./run_connector.sh

clean-connectors:
	cd connector && ./clean_connectors.sh
