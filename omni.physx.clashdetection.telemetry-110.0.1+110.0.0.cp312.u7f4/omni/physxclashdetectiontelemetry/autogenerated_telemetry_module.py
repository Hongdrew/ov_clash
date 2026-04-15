# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

# isort: off
# fmt: off

import omni.structuredlog
import json
import omni.log

# The JSON schema for these events
# The $ref statements for these events have been expanded because python's
# standard library json module can't expand $ref statements.
# If you want to distribute the jsonref package, you can use $ref statements.
schema = """
{
    "generated": "This was generated from clashdetection.structuredlog.schema.",
    "anyOf": [
        {
            "$ref": "#/definitions/events/com.nvidia.kit.physx.clashdetection.log_elapsed_query_run"
        },
        {
            "$ref": "#/definitions/events/com.nvidia.kit.physx.clashdetection.log_clash_data_file_size"
        },
        {
            "$ref": "#/definitions/events/com.nvidia.kit.physx.clashdetection.log_viewport_telemetry"
        },
        {
            "$ref": "#/definitions/events/com.nvidia.kit.physx.clashdetection.log_local_vs_remote_stage"
        },
        {
            "$ref": "#/definitions/events/com.nvidia.kit.physx.clashdetection.log_soft_vs_hard_query"
        },
        {
            "$ref": "#/definitions/events/com.nvidia.kit.physx.clashdetection.log_dynamic_vs_static_query"
        },
        {
            "$ref": "#/definitions/events/com.nvidia.kit.physx.clashdetection.log_num_of_found_overlaps"
        },
        {
            "$ref": "#/definitions/events/com.nvidia.kit.physx.clashdetection.log_used_system_memory"
        },
        {
            "$ref": "#/definitions/events/com.nvidia.kit.physx.clashdetection.log_total_num_of_overlapping_tris"
        },
        {
            "$ref": "#/definitions/events/com.nvidia.kit.physx.clashdetection.log_clash_data_meshes_stats"
        }
    ],
    "$schema": "http://json-schema.org/draft-07/schema#",
    "schemaMeta": {
        "clientName": "omni.physx.clashdetection",
        "schemaVersion": "1.1",
        "eventPrefix": "com.nvidia.kit.physx.clashdetection",
        "definitionVersion": "1.0",
        "description": "omni.physx.clashdetection schema to track and improve the product."
    },
    "definitions": {
        "events": {
            "com.nvidia.kit.physx.clashdetection.log_elapsed_query_run": {
                "eventMeta": {
                    "service": "telemetry",
                    "privacy": {
                        "category": "performance",
                        "description": "Tracks Clash Detection query processing and serialization elapsed time for performance analysis. This information is crucial for identifying bottlenecks, optimizing query performance, and enhancing overall system efficiency."
                    },
                    "omniverseFlags": []
                },
                "type": "object",
                "additionalProperties": false,
                "required": [
                    "clash_processing_elapsed",
                    "clash_serialization_elapsed"
                ],
                "properties": {
                    "clash_processing_elapsed": {
                        "type": "number",
                        "omniverseFormat": "float32",
                        "description": "elapsed processing time"
                    },
                    "clash_serialization_elapsed": {
                        "type": "number",
                        "omniverseFormat": "float32",
                        "description": "elapsed serialization time"
                    }
                },
                "description": "Tracks Clash Detection query processing and serialization elapsed time"
            },
            "com.nvidia.kit.physx.clashdetection.log_clash_data_file_size": {
                "eventMeta": {
                    "service": "telemetry",
                    "privacy": {
                        "category": "usage",
                        "description": "Monitors the Clash Detection database file size on disk to understand usage patterns. This information helps in assessing storage requirements and planning for optimal system performance."
                    },
                    "omniverseFlags": []
                },
                "type": "object",
                "additionalProperties": false,
                "required": [
                    "database_disk_size_mb"
                ],
                "properties": {
                    "database_disk_size_mb": {
                        "type": "number",
                        "omniverseFormat": "float32",
                        "description": "size of the database in MegaBytes"
                    }
                },
                "description": "Tracks Clash Detection database size on disk"
            },
            "com.nvidia.kit.physx.clashdetection.log_viewport_telemetry": {
                "eventMeta": {
                    "service": "telemetry",
                    "privacy": {
                        "category": "usage",
                        "description": "Monitors Clash Detection secondary viewport usage and user interaction for usage analysis. This telemetry event provides insights into how users engage with the secondary viewport, helping to optimize features and enhance overall user experience."
                    },
                    "omniverseFlags": []
                },
                "type": "object",
                "additionalProperties": false,
                "required": [
                    "clash_viewport_telemetry"
                ],
                "properties": {
                    "clash_viewport_telemetry": {
                        "type": "object",
                        "properties": {
                            "inited_seconds": {
                                "type": "number",
                                "omniverseFormat": "float32",
                                "description": "seconds the secondary viewport has been active"
                            },
                            "focused_seconds": {
                                "type": "number",
                                "omniverseFormat": "float32",
                                "description": "seconds the secondary viewport has been focused (user interaction)"
                            },
                            "visible_seconds": {
                                "type": "number",
                                "omniverseFormat": "float32",
                                "description": "seconds the secondary viewport has been visible (no user interaction)"
                            }
                        },
                        "required": [
                            "inited_seconds",
                            "focused_seconds",
                            "visible_seconds"
                        ],
                        "description": "telemetry data for the secondary viewport"
                    }
                },
                "description": "Tracks Clash Detection secondary viewport usage and user interaction"
            },
            "com.nvidia.kit.physx.clashdetection.log_local_vs_remote_stage": {
                "eventMeta": {
                    "service": "telemetry",
                    "privacy": {
                        "category": "usage",
                        "description": "Monitors whether the opened stage was local or remote for usage analysis. This telemetry event provides insights into the distribution of local and remote stage usage."
                    },
                    "omniverseFlags": []
                },
                "type": "object",
                "additionalProperties": false,
                "required": [
                    "local"
                ],
                "properties": {
                    "local": {
                        "type": "boolean",
                        "description": "True if the opened stage was local, False if remote"
                    }
                },
                "description": "Logs if opened stage was local (True) or remote (False)"
            },
            "com.nvidia.kit.physx.clashdetection.log_soft_vs_hard_query": {
                "eventMeta": {
                    "service": "telemetry",
                    "privacy": {
                        "category": "usage",
                        "description": "Monitors whether the executed clash detection query was looking for soft or hard clashes for usage analysis. This telemetry event provides insights into the distribution of soft and hard clash queries."
                    },
                    "omniverseFlags": []
                },
                "type": "object",
                "additionalProperties": false,
                "required": [
                    "soft"
                ],
                "properties": {
                    "soft": {
                        "type": "boolean",
                        "description": "True if the clash detection query was looking for soft clashes, False if hard"
                    }
                },
                "description": "Logs if executed clash detection query was looking for soft (True) or hard (False) clashes"
            },
            "com.nvidia.kit.physx.clashdetection.log_dynamic_vs_static_query": {
                "eventMeta": {
                    "service": "telemetry",
                    "privacy": {
                        "category": "usage",
                        "description": "Monitors whether the executed clash detection query was dynamic or static for usage analysis. This telemetry event provides insights into the distribution of dynamic and static clash queries."
                    },
                    "omniverseFlags": []
                },
                "type": "object",
                "additionalProperties": false,
                "required": [
                    "dynamic"
                ],
                "properties": {
                    "dynamic": {
                        "type": "boolean",
                        "description": "True if the clash detection query was dynamic, False if static"
                    }
                },
                "description": "Logs if executed clash detection query was dynamic (True) or static (False)"
            },
            "com.nvidia.kit.physx.clashdetection.log_num_of_found_overlaps": {
                "eventMeta": {
                    "service": "telemetry",
                    "privacy": {
                        "category": "usage",
                        "description": "Monitors the number of overlaps (clashes) found during the clash detection process for usage analysis. This telemetry event provides insights into the frequency of clash detections."
                    },
                    "omniverseFlags": []
                },
                "type": "object",
                "additionalProperties": false,
                "required": [
                    "num_overlaps"
                ],
                "properties": {
                    "num_overlaps": {
                        "type": "integer",
                        "description": "Number of overlaps found during the clash detection process"
                    }
                },
                "description": "Logs number of overlaps (clashes) found during the clash detection process"
            },
            "com.nvidia.kit.physx.clashdetection.log_used_system_memory": {
                "eventMeta": {
                    "service": "telemetry",
                    "privacy": {
                        "category": "performance",
                        "description": "Tracks the used system memory for the executed clash detection process in bytes for performance analysis. This information is crucial for understanding memory requirements and optimizing overall system efficiency."
                    },
                    "omniverseFlags": []
                },
                "type": "object",
                "additionalProperties": false,
                "required": [
                    "memory_size"
                ],
                "properties": {
                    "memory_size": {
                        "type": "integer",
                        "description": "Used system memory for the executed clash detection process in bytes"
                    }
                },
                "description": "Logs used system memory for the executed clash detection process in bytes"
            },
            "com.nvidia.kit.physx.clashdetection.log_total_num_of_overlapping_tris": {
                "eventMeta": {
                    "service": "telemetry",
                    "privacy": {
                        "category": "usage",
                        "description": "Monitors the total number of overlapping triangles found during the clash detection process for usage analysis. This telemetry event provides insights into the complexity of clash scenarios and helps in optimizing triangle-related processes."
                    },
                    "omniverseFlags": []
                },
                "type": "object",
                "additionalProperties": false,
                "required": [
                    "num_triangles"
                ],
                "properties": {
                    "num_triangles": {
                        "type": "integer",
                        "description": "Total number of overlapping triangles found during the clash detection process"
                    }
                },
                "description": "Logs total number of overlapping triangles found during the clash detection process"
            },
            "com.nvidia.kit.physx.clashdetection.log_clash_data_meshes_stats": {
                "eventMeta": {
                    "service": "telemetry",
                    "privacy": {
                        "category": "usage",
                        "description": "Monitors Clash Detection stats on the meshes involved in the clash detection. This telemetry event provides insights into how user queries result in meshes usage among multiple clash checks. Can be used to improve user experience and scaling efficiency."
                    },
                    "omniverseFlags": []
                },
                "type": "object",
                "additionalProperties": false,
                "required": [
                    "meshes_stats"
                ],
                "properties": {
                    "meshes_stats": {
                        "type": "object",
                        "properties": {
                            "nbMeshes": {
                                "type": "integer",
                                "omniverseFormat": "uint32",
                                "description": "number of meshes involved in the clash detection query run"
                            },
                            "nbSharedMeshes": {
                                "type": "integer",
                                "omniverseFormat": "uint32",
                                "description": "number of shared meshes (meshes with the same geometry/topology but located in different places)"
                            },
                            "nbCookedMeshes": {
                                "type": "integer",
                                "omniverseFormat": "uint32",
                                "description": "number of cooked meshes in the clash detection query run"
                            }
                        },
                        "required": [
                            "nbMeshes",
                            "nbSharedMeshes",
                            "nbCookedMeshes"
                        ],
                        "description": "telemetry data for clash meshes stats"
                    }
                },
                "description": "Tracks Clash Detection clash data meshes stats."
            }
        }
    },
    "description": "omni.physx.clashdetection schema to track and improve the product."
}
"""

# the telemetry events dictionary we can use to send events
events = None
try:
    schema = json.loads(schema)
    events = omni.structuredlog.register_schema(schema)
except Exception as e:
    omni.log.error("failed to register the schema: " + str(type(e)) + " " + str(e))

# These are wrappers for the send functions that you can call to send telemetry events
def log_elapsed_query_run_send_event(clash_processing_elapsed, clash_serialization_elapsed):
    """
    Helper function to send the com.nvidia.kit.physx.clashdetection.log_elapsed_query_run event.
    Tracks Clash Detection query processing and serialization elapsed
    time
    Args:
        clash_processing_elapsed: elapsed processing time
        clash_serialization_elapsed: elapsed serialization time
    Returns: no return value.
    """
    if events is None:
        return

    try:
        omni.structuredlog.send_event(events["log_elapsed_query_run"], {"clash_processing_elapsed": clash_processing_elapsed, "clash_serialization_elapsed": clash_serialization_elapsed})
    except Exception as e:
        omni.log.error("failed to send telemetry event log_elapsed_query_run " + str(type(e)) + " " + str(e))


def log_clash_data_file_size_send_event(database_disk_size_mb):
    """
    Helper function to send the com.nvidia.kit.physx.clashdetection.log_clash_data_file_size event.
    Tracks Clash Detection database size on disk
    Args:
        database_disk_size_mb: size of the database in MegaBytes
    Returns: no return value.
    """
    if events is None:
        return

    try:
        omni.structuredlog.send_event(events["log_clash_data_file_size"], {"database_disk_size_mb": database_disk_size_mb})
    except Exception as e:
        omni.log.error("failed to send telemetry event log_clash_data_file_size " + str(type(e)) + " " + str(e))


def log_viewport_telemetry_send_event(clash_viewport_telemetry):
    """
    Helper function to send the com.nvidia.kit.physx.clashdetection.log_viewport_telemetry event.
    Tracks Clash Detection secondary viewport usage and user
    interaction
    Args:
        clash_viewport_telemetry: telemetry data for the secondary viewport
                                  This structure must be passed as a dict.
                                  A dict with incorrect structure or types will not be sent.
    Returns: no return value.
    """
    if events is None:
        return

    try:
        omni.structuredlog.send_event(events["log_viewport_telemetry"], {"clash_viewport_telemetry": clash_viewport_telemetry})
    except Exception as e:
        omni.log.error("failed to send telemetry event log_viewport_telemetry " + str(type(e)) + " " + str(e))


def log_local_vs_remote_stage_send_event(local):
    """
    Helper function to send the com.nvidia.kit.physx.clashdetection.log_local_vs_remote_stage event.
    Logs if opened stage was local (True) or remote (False)
    Args:
        local: True if the opened stage was local, False if remote
    Returns: no return value.
    """
    if events is None:
        return

    try:
        omni.structuredlog.send_event(events["log_local_vs_remote_stage"], {"local": local})
    except Exception as e:
        omni.log.error("failed to send telemetry event log_local_vs_remote_stage " + str(type(e)) + " " + str(e))


def log_soft_vs_hard_query_send_event(soft):
    """
    Helper function to send the com.nvidia.kit.physx.clashdetection.log_soft_vs_hard_query event.
    Logs if executed clash detection query was looking for soft (True)
    or hard (False) clashes
    Args:
        soft: True if the clash detection query was looking for soft clashes,
              False if hard
    Returns: no return value.
    """
    if events is None:
        return

    try:
        omni.structuredlog.send_event(events["log_soft_vs_hard_query"], {"soft": soft})
    except Exception as e:
        omni.log.error("failed to send telemetry event log_soft_vs_hard_query " + str(type(e)) + " " + str(e))


def log_dynamic_vs_static_query_send_event(dynamic):
    """
    Helper function to send the com.nvidia.kit.physx.clashdetection.log_dynamic_vs_static_query event.
    Logs if executed clash detection query was dynamic (True) or
    static (False)
    Args:
        dynamic: True if the clash detection query was dynamic, False if static
    Returns: no return value.
    """
    if events is None:
        return

    try:
        omni.structuredlog.send_event(events["log_dynamic_vs_static_query"], {"dynamic": dynamic})
    except Exception as e:
        omni.log.error("failed to send telemetry event log_dynamic_vs_static_query " + str(type(e)) + " " + str(e))


def log_num_of_found_overlaps_send_event(num_overlaps):
    """
    Helper function to send the com.nvidia.kit.physx.clashdetection.log_num_of_found_overlaps event.
    Logs number of overlaps (clashes) found during the clash detection
    process
    Args:
        num_overlaps: Number of overlaps found during the clash detection process
    Returns: no return value.
    """
    if events is None:
        return

    try:
        omni.structuredlog.send_event(events["log_num_of_found_overlaps"], {"num_overlaps": num_overlaps})
    except Exception as e:
        omni.log.error("failed to send telemetry event log_num_of_found_overlaps " + str(type(e)) + " " + str(e))


def log_used_system_memory_send_event(memory_size):
    """
    Helper function to send the com.nvidia.kit.physx.clashdetection.log_used_system_memory event.
    Logs used system memory for the executed clash detection process
    in bytes
    Args:
        memory_size: Used system memory for the executed clash detection process in
                     bytes
    Returns: no return value.
    """
    if events is None:
        return

    try:
        omni.structuredlog.send_event(events["log_used_system_memory"], {"memory_size": memory_size})
    except Exception as e:
        omni.log.error("failed to send telemetry event log_used_system_memory " + str(type(e)) + " " + str(e))


def log_total_num_of_overlapping_tris_send_event(num_triangles):
    """
    Helper function to send the com.nvidia.kit.physx.clashdetection.log_total_num_of_overlapping_tris event.
    Logs total number of overlapping triangles found during the clash
    detection process
    Args:
        num_triangles: Total number of overlapping triangles found during the clash
                       detection process
    Returns: no return value.
    """
    if events is None:
        return

    try:
        omni.structuredlog.send_event(events["log_total_num_of_overlapping_tris"], {"num_triangles": num_triangles})
    except Exception as e:
        omni.log.error("failed to send telemetry event log_total_num_of_overlapping_tris " + str(type(e)) + " " + str(e))


def log_clash_data_meshes_stats_send_event(meshes_stats):
    """
    Helper function to send the com.nvidia.kit.physx.clashdetection.log_clash_data_meshes_stats event.
    Tracks Clash Detection clash data meshes stats.
    Args:
        meshes_stats: telemetry data for clash meshes stats
                      This structure must be passed as a dict.
                      A dict with incorrect structure or types will not be sent.
    Returns: no return value.
    """
    if events is None:
        return

    try:
        omni.structuredlog.send_event(events["log_clash_data_meshes_stats"], {"meshes_stats": meshes_stats})
    except Exception as e:
        omni.log.error("failed to send telemetry event log_clash_data_meshes_stats " + str(type(e)) + " " + str(e))
