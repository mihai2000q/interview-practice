import logging

import app.llm.timing  # noqa: F401  (sets up the logger; the level below must come after)

# Step timings are for the server log, not for test output.
logging.getLogger("app.timing").setLevel(logging.WARNING)
