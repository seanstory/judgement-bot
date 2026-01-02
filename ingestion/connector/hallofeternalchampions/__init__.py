#
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License 2.0;
# you may not use this file except in compliance with the Elastic License 2.0.
#
"""Hall of Eternal Champions connector package"""

from connectors.sources.hallofeternalchampions.client import (
    HallOfEternalChampionsClient,
)
from connectors.sources.hallofeternalchampions.datasource import (
    HallOfEternalChampionsDataSource,
)

__all__ = ["HallOfEternalChampionsDataSource", "HallOfEternalChampionsClient"]
