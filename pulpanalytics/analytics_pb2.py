# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: analytics.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder

# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(
    b'\n\x0f\x61nalytics.proto"\x84\x04\n\tAnalytics\x12\x11\n\tsystem_id\x18\x01 \x02(\t\x12\x39\n\x13online_content_apps\x18\x02 \x01(\x0b\x32\x1c.Analytics.OnlineContentApps\x12\x30\n\x0eonline_workers\x18\x03 \x01(\x0b\x32\x18.Analytics.OnlineWorkers\x12(\n\ncomponents\x18\x04 \x03(\x0b\x32\x14.Analytics.Component\x12\x1a\n\x12postgresql_version\x18\x05 \x01(\r\x12(\n\nrbac_stats\x18\x06 \x01(\x0b\x32\x14.Analytics.RBACStats\x1a\x35\n\x11OnlineContentApps\x12\x11\n\tprocesses\x18\x01 \x01(\r\x12\r\n\x05hosts\x18\x02 \x01(\r\x1a\x31\n\rOnlineWorkers\x12\x11\n\tprocesses\x18\x01 \x01(\r\x12\r\n\x05hosts\x18\x02 \x01(\r\x1a*\n\tComponent\x12\x0c\n\x04name\x18\x01 \x02(\t\x12\x0f\n\x07version\x18\x02 \x02(\t\x1aq\n\tRBACStats\x12\r\n\x05users\x18\x01 \x01(\r\x12\x0e\n\x06groups\x18\x02 \x01(\r\x12\x0f\n\x07\x64omains\x18\x03 \x01(\r\x12\x1e\n\x16\x63ustom_access_policies\x18\x04 \x01(\r\x12\x14\n\x0c\x63ustom_roles\x18\x05 \x01(\r'
)

_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, "analytics_pb2", globals())
if _descriptor._USE_C_DESCRIPTORS == False:
    DESCRIPTOR._options = None
    _ANALYTICS._serialized_start = 20
    _ANALYTICS._serialized_end = 536
    _ANALYTICS_ONLINECONTENTAPPS._serialized_start = 273
    _ANALYTICS_ONLINECONTENTAPPS._serialized_end = 326
    _ANALYTICS_ONLINEWORKERS._serialized_start = 328
    _ANALYTICS_ONLINEWORKERS._serialized_end = 377
    _ANALYTICS_COMPONENT._serialized_start = 379
    _ANALYTICS_COMPONENT._serialized_end = 421
    _ANALYTICS_RBACSTATS._serialized_start = 423
    _ANALYTICS_RBACSTATS._serialized_end = 536
# @@protoc_insertion_point(module_scope)
