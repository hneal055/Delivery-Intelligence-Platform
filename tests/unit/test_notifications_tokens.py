from src.backend.services.notifications import get_driver_token, register_driver_token


def test_registered_push_token_can_be_looked_up():
    register_driver_token("driver-x", "ExponentPushToken[abc]")
    assert get_driver_token("driver-x") == "ExponentPushToken[abc]"
    assert get_driver_token("nobody") is None
