from slowapi import Limiter
from slowapi.util import get_remote_address

# Limiter singleton — usa la IP del cliente como clave de rate limit.
# Se registra en app.state en main.py para que slowapi lo encuentre.
limiter = Limiter(key_func=get_remote_address)
