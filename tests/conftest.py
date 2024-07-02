import pytest

def pytest_addoption(parser):
    parser.addoption("--scim_url", action="store")
    parser.addoption("--bd_token", action="store")

@pytest.fixture
def scim_url(request):
    return request.config.getoption("--scim_url")

@pytest.fixture
def bd_token(request):
    return request.config.getoption("bd_token")

