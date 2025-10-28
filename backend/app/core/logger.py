# app/core/logger.py
import logging
import sys

LOG_FORMAT = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"

logging.basicConfig(
    level=logging.INFO, format=LOG_FORMAT, handlers=[logging.StreamHandler(sys.stdout)]
)

# Logger raíz de la aplicación
logger = logging.getLogger("app")
