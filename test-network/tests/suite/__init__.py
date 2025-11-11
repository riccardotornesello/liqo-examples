from .curl import test_curl
from .ping import test_ping

test_suite = {
    "ping": test_ping,
    "curl": test_curl,
}
