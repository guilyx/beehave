"""Allow ``python -m beehave``."""

from __future__ import annotations

import sys

from beehave.cli import main

sys.exit(main())
