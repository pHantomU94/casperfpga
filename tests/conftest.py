import pytest

from tests._helpers import FakeParent


@pytest.fixture
def fake_parent():
    return FakeParent()
