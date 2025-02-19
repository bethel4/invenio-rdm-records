# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 CERN.
# Copyright (C) 2020 Northwestern University.
# Copyright (C) 2021 TU Wien.
#
# Invenio-RDM-Records is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Pytest configuration.

See https://pytest-invenio.readthedocs.io/ for documentation on which test
fixtures are available.
"""

import pytest
from invenio_app.factory import create_api

from invenio_rdm_records.proxies import current_rdm_records_service


@pytest.fixture(scope="module")
def create_app(instance_path):
    """Application factory fixture."""
    return create_api


def link(url):
    """Strip the host part of a link."""
    api_prefix = "https://127.0.0.1:5000/api"
    if url.startswith(api_prefix):
        return url[len(api_prefix) :]
