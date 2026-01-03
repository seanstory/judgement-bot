FROM docker.elastic.co/integrations/elastic-connectors:9.4.0-SNAPSHOT

# Copy the custom connector source code to the venv site-packages
COPY hallofeternalchampions /app/app/connectors_service/.venv/lib/python3.11/site-packages/connectors/sources/hallofeternalchampions

# Install custom connector dependencies
# Note: This upgrades pydantic to 2.12.5, which elastic-connectors will warn about but works fine
RUN /app/bin/pip install -r /app/app/connectors_service/.venv/lib/python3.11/site-packages/connectors/sources/hallofeternalchampions/requirements.txt

# Install Chromium system dependencies from Chainguard repos
RUN apk update && apk add --no-cache \
    libnspr \
    libnss \
    glib \
    libx11 \
    libxcomposite \
    libxdamage \
    libxext \
    libxfixes \
    libxrandr \
    mesa-gbm \
    alsa-lib \
    at-spi2-core \
    libatk-1.0 \
    libatk-bridge-2.0 \
    cairo \
    cups-libs \
    dbus-libs \
    expat \
    libdrm \
    libxcb \
    libxkbcommon \
    pango \
    freetype \
    harfbuzz \
    libudev

# Install Playwright browsers
RUN /app/bin/playwright install chromium

# Add custom connector to config.py
# This will add the hallofeternalchampions connector to the CONNECTORS dict between graphql and jira
RUN sed -i '/"graphql":/a\            "hallofeternalchampions": "connectors.sources.hallofeternalchampions:HallOfEternalChampionsDataSource",' /app/app/connectors_service/connectors/config.py

# Copy custom config file that reads from environment variables
COPY config.yml /app/config.yml
