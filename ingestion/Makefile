.PHONY: install clean run ingest connector connector-base clean-connectors

install:
	pip install -r requirements.txt

clean:
	rm -rf output/

run:
	python3 parse_rulebook.py

ingest:
	python3 ingest.py

# Build the base connector image with all heavy dependencies
# This only needs to be run once, or when base dependencies change
connector-base:
	@echo "Building base connector image with dependencies..."
	cd connector && docker build -f Dockerfile.base -t judgement-connector-base:latest .
	@echo "Base image built successfully!"

# Build and run the connector (uses base image if available)
connector:
	cd connector && ./run_connector.sh

clean-connectors:
	cd connector && ./clean_connectors.sh
