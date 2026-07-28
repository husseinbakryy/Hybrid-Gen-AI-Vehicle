import logging
from pathlib import Path

formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Console Handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)

# Main Logger
logger = logging.getLogger("hybrid_vehicle")
logger.setLevel(logging.INFO)

if not logger.handlers:
    logger.addHandler(console_handler)
