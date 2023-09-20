import json
import logging
from urllib.parse import parse_qs, urlparse

import requests

DEFAULT_OPTIONS = {
    "encoding": "UTF-8",
    "separator": ",",
    "ignoreLines": -1,
    "headerLines": 1,
    "skipDataLines": 0,
    "limit": -1,
    "storeBlankRows": True,
    "guessCellValueTypes": False,
    "processQuotes": True,
    "quoteCharacter": '"',
    "storeBlankCellsAsNulls": True,
    "includeFileSources": False,
    "includeArchiveFileName": False,
    "trimStrings": False,
    "disableAutoPreview": False,
}


class OpenRefine:
    def __init__(self, url, public_url):
        self.url = url
        self.public_url = public_url
        self.csrf_token = None
        self.update_csrf_token()

    def update_csrf_token(self):
        response = self.request("get-csrf-token")
        parsed = response.json()
        self.csrf_token = parsed["token"]

    def request(self, command, method="GET", files=None, **params):
        if self.csrf_token:
            params["csrf_token"] = self.csrf_token
        response = requests.request(
            method,
            self.url + "/command/core/" + command,
            files=files,
            params=params,
            stream=True,
        )
        response.raise_for_status()
        return response

    def create_project(self, name, files, file_format, index=0, **options):
        all_options = DEFAULT_OPTIONS
        all_options.update(options)

        all_options["sheets"] = []
        form = []
        # https://requests.readthedocs.io/en/latest/user/advanced/#post-multiple-multipart-encoded-files
        for file in files:
            form.append(
                (
                    "project-file",
                    (
                        file["filename"],
                        file["content"],
                        file["mime_type"],
                    ),
                )
            )
            sheet = {"fileNameAndSheetIndex": file["filename"] + "#%d" % index}
            all_options["sheets"].append(sheet)
        form.extend(
            [
                ("project-name", (None, name)),
                ("format", (None, file_format)),
                ("options", (None, json.dumps(all_options))),
            ]
        )

        response = self.request("create-project-from-upload", method="POST", files=form)

        project = int(parse_qs(urlparse(response.url).query)["project"][0])

        # https://github.com/OpenRefine/OpenRefine/issues/5387
        self.get_rows(project)

        return project

    def get_rows(self, project, start=0, limit=0):
        response = self.request("get-rows", project=project, start=start, limit=limit)
        return response.json()

    def get_metadata(self, project):
        response = self.request("get-project-metadata", project=project)
        return response.json()

    def project_url(self, project):
        internal_url = requests.get(
            self.url + "/project", params={"project": project}
        ).url
        if not internal_url.startswith(self.url):
            logging.error(
                f"{self.url} differs from the URL of the project {internal_url}"
            )
            return internal_url
        return internal_url.replace(self.url, self.public_url, 1)

    def project_export(self, project, file_format="csv"):
        return self.request(
            "export-rows/csv",
            method="POST",
            project=project,
            format=file_format,
        )
