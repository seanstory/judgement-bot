# Use local base image if available, otherwise build from Dockerfile.base
ARG BASE_IMAGE=judgement-connector-base:latest
FROM ${BASE_IMAGE}

# Copy the custom connector source code to the venv site-packages
COPY hallofeternalchampions /app/app/connectors_service/.venv/lib/python3.11/site-packages/connectors/sources/hallofeternalchampions

# Install custom connector dependencies (only the ones not in base)
# Note: This upgrades pydantic to 2.12.5, which elastic-connectors will warn about but works fine
RUN /app/bin/pip install -r /app/app/connectors_service/.venv/lib/python3.11/site-packages/connectors/sources/hallofeternalchampions/requirements.txt

# Add custom connector to config.py
# This will add the hallofeternalchampions connector to the CONNECTORS dict between graphql and jira
RUN sed -i '/"graphql":/a\            "hallofeternalchampions": "connectors.sources.hallofeternalchampions:HallOfEternalChampionsDataSource",' /app/app/connectors_service/connectors/config.py

# Copy custom config file that reads from environment variables
COPY config.yml /app/config.yml
