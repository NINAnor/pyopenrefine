import re
from datetime import timedelta
from textwrap import dedent
from time import time

import pytest
from pytest_container import DerivedContainer
from pytest_container.container import ContainerBase, ContainerData
from pytest_container.inspect import ContainerHealth, PortForwarding

from pyopenrefine import OpenRefine

TAGS = ("master", "4.0", "3.7", "3.6.2")
IMAGES = [
    DerivedContainer(
        base=f"ghcr.io/ninanor/openrefine:{tag}",
        containerfile=dedent(
            """
        HEALTHCHECK --interval=1s --start-period=10s CMD curl -sSf -o /dev/null http://localhost:3333
        """
        ),
        forwarded_ports=[PortForwarding(container_port=3333)],
        healthcheck_timeout=timedelta(seconds=30),
    )
    for tag in TAGS
]

csv_file = {
    "filename": "test.csv",
    "content": b"col1,col2\n1,2\n3,4\n",
    "mime_type": "text/line-based/*sv",
    "last_modified": time(),
}


@pytest.mark.parametrize("container", IMAGES, indirect=True)
def test_health(container: ContainerData, container_runtime: ContainerBase):
    assert (
        container_runtime.get_container_health(container.container_id)
        == ContainerHealth.HEALTHY
    )


@pytest.mark.parametrize("container", IMAGES, indirect=True)
def test_csrf(container: ContainerData, container_runtime: ContainerBase):
    port = container.forwarded_ports[0].host_port
    url = f"http://localhost:{port}"
    openrefine = OpenRefine(url, url)
    assert len(openrefine.csrf_token) == 32


@pytest.mark.parametrize("container", IMAGES, indirect=True)
def test_create_project(container: ContainerData, container_runtime: ContainerBase):
    port = container.forwarded_ports[0].host_port
    url = f"http://localhost:{port}"
    openrefine = OpenRefine(url, url)
    project = openrefine.create_project(
        "test",
        [csv_file],
        csv_file["mime_type"],
    )
    assert isinstance(project, int)
    assert 0 < project
    metadata = openrefine.get_metadata(project)
    assert metadata["rowCount"] == csv_file["content"].count(b"\n")-1
    project_url = openrefine.project_url(project)
    assert re.match(r"^%s/project\?project=\d{13}$" % url, project_url)


@pytest.mark.parametrize("container", IMAGES, indirect=True)
def test_upload_download(container: ContainerData, container_runtime: ContainerBase):
    port = container.forwarded_ports[0].host_port
    url = f"http://localhost:{port}"
    openrefine = OpenRefine(url, url)
    project = openrefine.create_project(
        "test",
        [csv_file],
        csv_file["mime_type"],
    )
    export = openrefine.project_export(project)
    assert export.content == csv_file["content"]
