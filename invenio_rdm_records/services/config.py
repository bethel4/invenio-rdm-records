# -*- coding: utf-8 -*-
#
# Copyright (C) 2020-2021 CERN.
# Copyright (C) 2020-2021 Northwestern University.
# Copyright (C)      2021 TU Wien.
# Copyright (C) 2021-2023 Graz University of Technology.
# Copyright (C) 2022 Universität Hamburg
#
# Invenio-RDM-Records is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""RDM Record Service."""

from os.path import splitext

from flask import current_app
from invenio_communities.communities.records.api import Community
from invenio_drafts_resources.services.records.components import (
    DraftFilesComponent,
    PIDComponent,
    RelationsComponent,
)
from invenio_drafts_resources.services.records.config import (
    RecordServiceConfig,
    SearchDraftsOptions,
    SearchOptions,
    SearchVersionsOptions,
    is_draft,
    is_record,
)
from invenio_indexer.api import RecordIndexer
from invenio_records_resources.services import ConditionalLink, FileServiceConfig
from invenio_records_resources.services.base.config import (
    ConfiguratorMixin,
    FromConfig,
    FromConfigSearchOptions,
    SearchOptionsMixin,
    ServiceConfig,
)
from invenio_records_resources.services.base.links import Link
from invenio_records_resources.services.files.links import FileLink
from invenio_records_resources.services.records.config import (
    RecordServiceConfig as BaseRecordServiceConfig,
)
from invenio_records_resources.services.records.links import (
    RecordLink,
    pagination_links,
)
from invenio_requests.services.requests import RequestItem, RequestList
from invenio_requests.services.requests.config import RequestSearchOptions
from requests import Request

from ..records import RDMDraft, RDMRecord
from . import facets
from .components import (
    AccessComponent,
    CustomFieldsComponent,
    MetadataComponent,
    PIDsComponent,
    ReviewComponent,
)
from .customizations import FromConfigPIDsProviders, FromConfigRequiredPIDs
from .permissions import RDMRecordPermissionPolicy
from .result_items import SecretLinkItem, SecretLinkList
from .schemas import RDMParentSchema, RDMRecordSchema
from .schemas.community_records import CommunityRecordsSchema
from .schemas.parent.access import SecretLink
from .schemas.record_communities import RecordCommunitiesSchema


def is_draft_and_has_review(record, ctx):
    """Determine if submit review link should be included."""
    return is_draft(record, ctx) and record.parent.review is not None


def is_record_and_has_doi(record, ctx):
    """Determine if submit review link should be included."""
    return is_record(record, ctx) and has_doi(record, ctx)


def has_doi(record, ctx):
    """Determine if a record has a DOI."""
    pids = record.pids or {}
    return "doi" in pids


def is_iiif_compatible(file_, ctx):
    """Determine if a file is IIIF compatible."""
    file_ext = splitext(file_.key)[1].replace(".", "").lower()
    return file_ext in current_app.config["IIIF_FORMATS"]


def archive_download_enabled(record, ctx):
    """Return if the archive download feature is enabled."""
    return current_app.config["RDM_ARCHIVE_DOWNLOAD_ENABLED"]


def is_datacite_test(record, ctx):
    """Return if the datacite test mode is being used."""
    return current_app.config["DATACITE_TEST_MODE"]


#
# Default search configuration
#
class RDMSearchOptions(SearchOptions, SearchOptionsMixin):
    """Search options for record search."""

    facets = {
        "resource_type": facets.resource_type,
        "languages": facets.language,
        "access_status": facets.access_status,
    }


class RDMSearchDraftsOptions(SearchDraftsOptions, SearchOptionsMixin):
    """Search options for drafts search."""

    facets = {
        "resource_type": facets.resource_type,
        "languages": facets.language,
        "access_status": facets.access_status,
        "is_published": facets.is_published,
    }


class RDMSearchVersionsOptions(SearchVersionsOptions, SearchOptionsMixin):
    """Search options for record versioning search."""


class RDMRecordCommunitiesConfig(ServiceConfig, ConfiguratorMixin):
    """Record communities service config."""

    service_id = "record-communities"
    record_cls = RDMRecord
    permission_policy_cls = FromConfig(
        "RDM_PERMISSION_POLICY", default=RDMRecordPermissionPolicy, import_string=True
    )

    schema = RecordCommunitiesSchema

    indexer_cls = RecordIndexer
    indexer_queue_name = service_id
    index_dumper = None

    # Max n. communities that can be added at once
    max_number_of_additions = 10
    # Max n. communities that can be removed at once
    max_number_of_removals = 10


class RDMRecordRequestsConfig(ServiceConfig, ConfiguratorMixin):
    """Record community inclusion config."""

    request_record_cls = RDMRecord
    service_id = "record-requests"
    permission_policy_cls = FromConfig(
        "RDM_PERMISSION_POLICY", default=RDMRecordPermissionPolicy, import_string=True
    )
    result_item_cls = RequestItem
    result_list_cls = RequestList
    search = RequestSearchOptions

    # request-specific configuration
    record_cls = Request  # needed for model queries
    schema = None  # stored in the API classes, for customization
    indexer_queue_name = "requests"
    index_dumper = None


class RDMCommunityRecordsConfig(BaseRecordServiceConfig, ConfiguratorMixin):
    """Community records service config."""

    service_id = "community-records"
    record_cls = RDMRecord
    community_cls = Community
    permission_policy_cls = FromConfig(
        "RDM_PERMISSION_POLICY", default=RDMRecordPermissionPolicy, import_string=True
    )

    # Search configuration
    search = FromConfigSearchOptions(
        "RDM_SEARCH",
        "RDM_SORT_OPTIONS",
        "RDM_FACETS",
        search_option_cls=RDMSearchOptions,
    )
    search_versions = FromConfigSearchOptions(
        "RDM_SEARCH_VERSIONING",
        "RDM_SORT_OPTIONS",
        "RDM_FACETS",
        search_option_cls=RDMSearchVersionsOptions,
    )

    # Service schemas
    community_record_schema = CommunityRecordsSchema
    schema = RDMRecordSchema

    # Max n. records that can be removed at once
    max_number_of_removals = 10

    links_search_community_records = pagination_links(
        "{+api}/communities/{id}/records{?args*}"
    )


#
# Default service configuration
#
class RDMRecordServiceConfig(RecordServiceConfig, ConfiguratorMixin):
    """RDM record draft service config."""

    # Record and draft classes
    record_cls = RDMRecord
    draft_cls = RDMDraft

    # Schemas
    schema = RDMRecordSchema
    schema_parent = RDMParentSchema
    schema_secret_link = SecretLink

    # Permission policy
    permission_policy_cls = FromConfig(
        "RDM_PERMISSION_POLICY", default=RDMRecordPermissionPolicy, import_string=True
    )

    # Result classes
    link_result_item_cls = SecretLinkItem
    link_result_list_cls = SecretLinkList

    # Search configuration
    search = FromConfigSearchOptions(
        "RDM_SEARCH",
        "RDM_SORT_OPTIONS",
        "RDM_FACETS",
        search_option_cls=RDMSearchOptions,
    )
    search_drafts = FromConfigSearchOptions(
        "RDM_SEARCH_DRAFTS",
        "RDM_SORT_OPTIONS",
        "RDM_FACETS",
        search_option_cls=RDMSearchDraftsOptions,
    )
    search_versions = FromConfigSearchOptions(
        "RDM_SEARCH_VERSIONING",
        "RDM_SORT_OPTIONS",
        "RDM_FACETS",
        search_option_cls=RDMSearchVersionsOptions,
    )

    # PIDs configuration
    pids_providers = FromConfigPIDsProviders()
    pids_required = FromConfigRequiredPIDs()

    # Components - order matters!
    components = [
        MetadataComponent,
        CustomFieldsComponent,
        AccessComponent,
        DraftFilesComponent,
        # for the internal `pid` field
        PIDComponent,
        # for the `pids` field (external PIDs)
        PIDsComponent,
        RelationsComponent,
        ReviewComponent,
    ]

    # Links
    links_item = {
        "self": ConditionalLink(
            cond=is_record,
            if_=RecordLink("{+api}/records/{id}"),
            else_=RecordLink("{+api}/records/{id}/draft"),
        ),
        "self_html": ConditionalLink(
            cond=is_record,
            if_=RecordLink("{+ui}/records/{id}"),
            else_=RecordLink("{+ui}/uploads/{id}"),
        ),
        "self_doi": Link(
            "{+ui}/doi/{+pid_doi}",
            when=is_record_and_has_doi,
            vars=lambda record, vars: vars.update(
                {
                    f"pid_{scheme}": pid["identifier"]
                    for (scheme, pid) in record.pids.items()
                }
            ),
        ),
        "doi": ConditionalLink(
            cond=is_datacite_test,
            if_=Link(
                "https://handle.stage.datacite.org/{+pid_doi}",
                when=has_doi,
                vars=lambda record, vars: vars.update(
                    {
                        f"pid_{scheme}": pid["identifier"]
                        for (scheme, pid) in record.pids.items()
                    }
                ),
            ),
            else_=Link(
                "https://doi.org/{+pid_doi}",
                when=has_doi,
                vars=lambda record, vars: vars.update(
                    {
                        f"pid_{scheme}": pid["identifier"]
                        for (scheme, pid) in record.pids.items()
                    }
                ),
            ),
        ),
        "self_iiif_manifest": ConditionalLink(
            cond=is_record,
            if_=RecordLink("{+api}/iiif/record:{id}/manifest"),
            else_=RecordLink("{+api}/iiif/draft:{id}/manifest"),
        ),
        "self_iiif_sequence": ConditionalLink(
            cond=is_record,
            if_=RecordLink("{+api}/iiif/record:{id}/sequence/default"),
            else_=RecordLink("{+api}/iiif/draft:{id}/sequence/default"),
        ),
        "files": ConditionalLink(
            cond=is_record,
            if_=RecordLink("{+api}/records/{id}/files"),
            else_=RecordLink("{+api}/records/{id}/draft/files"),
        ),
        "archive": ConditionalLink(
            cond=is_record,
            if_=RecordLink(
                "{+api}/records/{id}/files-archive",
                when=archive_download_enabled,
            ),
            else_=RecordLink(
                "{+api}/records/{id}/draft/files-archive",
                when=archive_download_enabled,
            ),
        ),
        "latest": RecordLink("{+api}/records/{id}/versions/latest", when=is_record),
        "latest_html": RecordLink("{+ui}/records/{id}/latest", when=is_record),
        "draft": RecordLink("{+api}/records/{id}/draft", when=is_record),
        "record": RecordLink("{+api}/records/{id}", when=is_draft),
        # TODO: record_html temporarily needed for DOI registration, until
        # problems with self_doi has been fixed
        "record_html": RecordLink("{+ui}/records/{id}", when=is_draft),
        "publish": RecordLink(
            "{+api}/records/{id}/draft/actions/publish", when=is_draft
        ),
        "review": RecordLink("{+api}/records/{id}/draft/review", when=is_draft),
        "submit-review": RecordLink(
            "{+api}/records/{id}/draft/actions/submit-review",
            when=is_draft_and_has_review,
        ),
        "versions": RecordLink("{+api}/records/{id}/versions"),
        "access_links": RecordLink("{+api}/records/{id}/access/links"),
        # TODO: only include link when DOI support is enabled.
        "reserve_doi": RecordLink("{+api}/records/{id}/draft/pids/doi"),
        "communities": RecordLink("{+api}/records/{id}/communities"),
        "communities-suggestions": RecordLink(
            "{+api}/records/{id}/communities-suggestions"
        ),
        "requests": RecordLink("{+api}/records/{id}/requests"),
    }


class RDMFileRecordServiceConfig(FileServiceConfig, ConfiguratorMixin):
    """Configuration for record files."""

    record_cls = RDMRecord
    permission_policy_cls = FromConfig(
        "RDM_PERMISSION_POLICY", default=RDMRecordPermissionPolicy
    )

    file_links_list = {
        **FileServiceConfig.file_links_list,
        "archive": RecordLink(
            "{+api}/records/{id}/files-archive",
            when=archive_download_enabled,
        ),
    }

    file_links_item = {
        **FileServiceConfig.file_links_item,
        # FIXME: filename instead
        "iiif_canvas": FileLink(
            "{+api}/iiif/record:{id}/canvas/{key}", when=is_iiif_compatible
        ),
        "iiif_base": FileLink("{+api}/iiif/record:{id}:{key}", when=is_iiif_compatible),
        "iiif_info": FileLink(
            "{+api}/iiif/record:{id}:{key}/info.json", when=is_iiif_compatible
        ),
        "iiif_api": FileLink(
            "{+api}/iiif/record:{id}:{key}/{region=full}"
            "/{size=full}/{rotation=0}/{quality=default}.{format=png}",
            when=is_iiif_compatible,
        ),
    }


class RDMFileDraftServiceConfig(FileServiceConfig, ConfiguratorMixin):
    """Configuration for draft files."""

    service_id = "draft-files"

    record_cls = RDMDraft
    permission_action_prefix = "draft_"
    permission_policy_cls = FromConfig(
        "RDM_PERMISSION_POLICY", default=RDMRecordPermissionPolicy
    )

    file_links_list = {
        "self": RecordLink("{+api}/records/{id}/draft/files"),
        "archive": RecordLink(
            "{+api}/records/{id}/draft/files-archive",
            when=archive_download_enabled,
        ),
    }

    file_links_item = {
        "self": FileLink("{+api}/records/{id}/draft/files/{key}"),
        "content": FileLink("{+api}/records/{id}/draft/files/{key}/content"),
        "commit": FileLink("{+api}/records/{id}/draft/files/{key}/commit"),
        # FIXME: filename instead
        "iiif_canvas": FileLink(
            "{+api}/iiif/draft:{id}/canvas/{key}", when=is_iiif_compatible
        ),
        "iiif_base": FileLink("{+api}/iiif/draft:{id}:{key}", when=is_iiif_compatible),
        "iiif_info": FileLink(
            "{+api}/iiif/draft:{id}:{key}/info.json", when=is_iiif_compatible
        ),
        "iiif_api": FileLink(
            "{+api}/iiif/draft:{id}:{key}/{region=full}"
            "/{size=full}/{rotation=0}/{quality=default}.{format=png}",
            when=is_iiif_compatible,
        ),
    }
