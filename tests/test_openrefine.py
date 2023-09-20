from datetime import timedelta

import pytest
from pytest_container import Container
from pytest_container.container import ContainerData
from pytest_container.inspect import ContainerHealth

TAGS = ("master", "4.0", "3.7", "3.6.2")
IMAGES = [
    Container(
        url=f"ghcr.io/ninanor/openrefine:{tag}",
        healthcheck_timeout=timedelta(seconds=60),
    )
    for tag in TAGS
]


@pytest.mark.parametrize("container", IMAGES, indirect=["container"])
def test_health(container: ContainerData, container_runtime):
    assert (
        container_runtime.get_container_health(container.container_id)
        == ContainerHealth.HEALTHY
    )
