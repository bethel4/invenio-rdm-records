# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 CERN.
# Copyright (C) 2022 Universität Hamburg.
#
# Invenio-RDM-Records is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""High-level API for wokring with RDM records, files, pids and search."""
from .community_records import CommunityRecordsService
from .config import (
    RDMCommunityRecordsConfig,
    RDMFileDraftServiceConfig,
    RDMFileRecordServiceConfig,
    RDMRecordCommunitiesConfig,
    RDMRecordRequestsConfig,
    RDMRecordServiceConfig,
)
from .iiif import IIIFService
from .permissions import RDMRecordPermissionPolicy
from .requests import RecordRequestsService
from .secret_links import SecretLinkService
from .services import RDMRecordService

__all__ = (
    "IIIFService",
    "RDMFileDraftServiceConfig",
    "RDMFileRecordServiceConfig",
    "RDMRecordPermissionPolicy",
    "RDMRecordService",
    "RDMRecordServiceConfig",
    "SecretLinkService",
    "RDMRecordCommunitiesConfig",
    "RDMCommunityRecordsConfig",
    "CommunityRecordsService",
    "RDMRecordRequestsConfig",
    "RecordRequestsService",
)
