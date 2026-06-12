"""Service-layer + middleware unit test package (catalog-form backend slice).

Hosts pure-function unit tests that mock external systems (Gemini, DB, Valkey)
so they run without the dev tunnel.  Marked ``@pytest.mark.unit`` per §19.D.
"""
