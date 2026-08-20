from tests.parity.conftest import _binary_name


def test_parity_binary_name_matches_cargo_platform_convention():
    assert _binary_name("nt") == "v8-core.exe"
    assert _binary_name("posix") == "v8-core"
