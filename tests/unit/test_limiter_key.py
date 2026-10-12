"""Rate limits are per visitor, not per proxy."""
from starlette.requests import Request

from src.backend.api.limiter import client_key


def req(headers=(), client="172.18.0.6"):
    return Request({
        "type": "http", "method": "POST", "path": "/auth/token", "query_string": b"",
        "headers": [(k.encode(), v.encode()) for k, v in headers],
        "client": (client, 50000),
    })


def test_internet_visitor_keyed_by_cloudflare_address():
    r = req([("cf-connecting-ip", "203.0.113.9"), ("x-real-ip", "172.18.0.7")])
    assert client_key(r) == "203.0.113.9"


def test_office_browser_keyed_by_nginx_real_ip():
    assert client_key(req([("x-real-ip", "192.168.12.140")])) == "192.168.12.140"


def test_direct_connection_falls_back_to_socket_address():
    assert client_key(req(client="127.0.0.1")) == "127.0.0.1"


def test_two_visitors_get_separate_buckets():
    a = client_key(req([("cf-connecting-ip", "203.0.113.9")]))
    b = client_key(req([("cf-connecting-ip", "198.51.100.4")]))
    assert a != b
