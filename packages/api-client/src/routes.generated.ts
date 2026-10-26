/* Generated from the unique OpenAPI source. Do not edit. */
export const ROUTES = {
  "GET /api/v1/health": {
    "method": "GET",
    "template": "/api/v1/health",
    "operationId": "health_api_v1_health_get",
    "requestMedia": [],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "GET /api/v1/projects": {
    "method": "GET",
    "template": "/api/v1/projects",
    "operationId": "projects_api_v1_projects_get",
    "requestMedia": [],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "POST /api/v1/projects": {
    "method": "POST",
    "template": "/api/v1/projects",
    "operationId": "project_create_api_v1_projects_post",
    "requestMedia": [
      "application/json"
    ],
    "responseMedia": {
      "201": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "GET /api/v1/assets": {
    "method": "GET",
    "template": "/api/v1/assets",
    "operationId": "asset_list_api_v1_assets_get",
    "requestMedia": [],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "GET /api/v1/credentials": {
    "method": "GET",
    "template": "/api/v1/credentials",
    "operationId": "credential_list_api_v1_credentials_get",
    "requestMedia": [],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "POST /api/v1/credentials": {
    "method": "POST",
    "template": "/api/v1/credentials",
    "operationId": "credential_create_api_v1_credentials_post",
    "requestMedia": [
      "application/json"
    ],
    "responseMedia": {
      "201": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "DELETE /api/v1/credentials/{ref}": {
    "method": "DELETE",
    "template": "/api/v1/credentials/{ref}",
    "operationId": "credential_delete_api_v1_credentials__ref__delete",
    "requestMedia": [],
    "responseMedia": {
      "204": [],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "GET /api/v1/projects/{project_id}": {
    "method": "GET",
    "template": "/api/v1/projects/{project_id}",
    "operationId": "project_get_api_v1_projects__project_id__get",
    "requestMedia": [],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "PUT /api/v1/projects/{project_id}": {
    "method": "PUT",
    "template": "/api/v1/projects/{project_id}",
    "operationId": "project_update_api_v1_projects__project_id__put",
    "requestMedia": [
      "application/json"
    ],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "GET /api/v1/productions": {
    "method": "GET",
    "template": "/api/v1/productions",
    "operationId": "production_list_api_v1_productions_get",
    "requestMedia": [],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "POST /api/v1/productions": {
    "method": "POST",
    "template": "/api/v1/productions",
    "operationId": "production_create_api_v1_productions_post",
    "requestMedia": [
      "application/json"
    ],
    "responseMedia": {
      "202": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "POST /api/v1/project-goals": {
    "method": "POST",
    "template": "/api/v1/project-goals",
    "operationId": "create_project_goal",
    "requestMedia": [
      "application/json"
    ],
    "responseMedia": {
      "202": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "POST /api/v1/project-goals/receipt-lookup": {
    "method": "POST",
    "template": "/api/v1/project-goals/receipt-lookup",
    "operationId": "lookup_project_goal_receipt",
    "requestMedia": [
      "application/json"
    ],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "GET /api/v1/productions/{production_id}": {
    "method": "GET",
    "template": "/api/v1/productions/{production_id}",
    "operationId": "production_get_api_v1_productions__production_id__get",
    "requestMedia": [],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "GET /api/v1/budget": {
    "method": "GET",
    "template": "/api/v1/budget",
    "operationId": "budget_summary_api_v1_budget_get",
    "requestMedia": [],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "POST /api/v1/productions/preview": {
    "method": "POST",
    "template": "/api/v1/productions/preview",
    "operationId": "production_preview_api_v1_productions_preview_post",
    "requestMedia": [
      "application/json"
    ],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "GET /api/v1/capabilities": {
    "method": "GET",
    "template": "/api/v1/capabilities",
    "operationId": "capability_list_api_v1_capabilities_get",
    "requestMedia": [],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "POST /api/v1/productions/{production_id}/publish": {
    "method": "POST",
    "template": "/api/v1/productions/{production_id}/publish",
    "operationId": "production_publish_api_v1_productions__production_id__publish_post",
    "requestMedia": [],
    "responseMedia": {
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "POST /api/v1/productions/{production_id}/cancel": {
    "method": "POST",
    "template": "/api/v1/productions/{production_id}/cancel",
    "operationId": "production_cancel_api_v1_productions__production_id__cancel_post",
    "requestMedia": [],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "GET /api/v1/productions/{production_id}/revisions": {
    "method": "GET",
    "template": "/api/v1/productions/{production_id}/revisions",
    "operationId": "production_revisions_api_v1_productions__production_id__revisions_get",
    "requestMedia": [],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "POST /api/v1/runs/{run_id}/decisions": {
    "method": "POST",
    "template": "/api/v1/runs/{run_id}/decisions",
    "operationId": "decision_submit_api_v1_runs__run_id__decisions_post",
    "requestMedia": [
      "application/json"
    ],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "POST /api/v1/runs/{run_id}/pause": {
    "method": "POST",
    "template": "/api/v1/runs/{run_id}/pause",
    "operationId": "run_pause_api_v1_runs__run_id__pause_post",
    "requestMedia": [],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "POST /api/v1/runs/{run_id}/resume": {
    "method": "POST",
    "template": "/api/v1/runs/{run_id}/resume",
    "operationId": "run_resume_api_v1_runs__run_id__resume_post",
    "requestMedia": [],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "GET /api/v1/runs/{run_id}/events": {
    "method": "GET",
    "template": "/api/v1/runs/{run_id}/events",
    "operationId": "run_events_api_v1_runs__run_id__events_get",
    "requestMedia": [],
    "responseMedia": {
      "200": [
        "application/json",
        "text/event-stream"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "POST /api/v1/assets/staging": {
    "method": "POST",
    "template": "/api/v1/assets/staging",
    "operationId": "asset_stage_api_v1_assets_staging_post",
    "requestMedia": [
      "*/*"
    ],
    "responseMedia": {
      "201": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "POST /api/v1/assets/import": {
    "method": "POST",
    "template": "/api/v1/assets/import",
    "operationId": "asset_import_api_v1_assets_import_post",
    "requestMedia": [
      "application/json"
    ],
    "responseMedia": {
      "201": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "GET /api/v1/assets/{asset_id}": {
    "method": "GET",
    "template": "/api/v1/assets/{asset_id}",
    "operationId": "asset_get_api_v1_assets__asset_id__get",
    "requestMedia": [],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "GET /api/v1/assets/{asset_id}/content": {
    "method": "GET",
    "template": "/api/v1/assets/{asset_id}/content",
    "operationId": "asset_content_api_v1_assets__asset_id__content_get",
    "requestMedia": [],
    "responseMedia": {
      "200": [
        "*/*"
      ],
      "206": [
        "*/*",
        "multipart/byteranges"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "416": [
        "text/plain"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "GET /api/v1/assets/{asset_id}/content/metadata": {
    "method": "GET",
    "template": "/api/v1/assets/{asset_id}/content/metadata",
    "operationId": "asset_content_metadata_api_v1_assets__asset_id__content_metadata_get",
    "requestMedia": [],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "GET /api/v1/bundles/{revision_id}/manifest": {
    "method": "GET",
    "template": "/api/v1/bundles/{revision_id}/manifest",
    "operationId": "bundle_get_api_v1_bundles__revision_id__manifest_get",
    "requestMedia": [],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "206": [
        "application/json",
        "multipart/byteranges"
      ],
      "304": [],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "416": [
        "text/plain"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "GET /api/v1/bundles/{revision_id}/manifest/metadata": {
    "method": "GET",
    "template": "/api/v1/bundles/{revision_id}/manifest/metadata",
    "operationId": "bundle_manifest_metadata_api_v1_bundles__revision_id__manifest_metadata_get",
    "requestMedia": [],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "GET /api/v1/bundles/{revision_id}/artifacts/{artifact_id}/content": {
    "method": "GET",
    "template": "/api/v1/bundles/{revision_id}/artifacts/{artifact_id}/content",
    "operationId": "bundle_content_api_v1_bundles__revision_id__artifacts__artifact_id__content_get",
    "requestMedia": [],
    "responseMedia": {
      "200": [
        "*/*"
      ],
      "206": [
        "*/*",
        "multipart/byteranges"
      ],
      "304": [],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "416": [
        "text/plain"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "GET /api/v1/bundles/{revision_id}/artifacts/{artifact_id}/content/metadata": {
    "method": "GET",
    "template": "/api/v1/bundles/{revision_id}/artifacts/{artifact_id}/content/metadata",
    "operationId": "bundle_artifact_metadata_api_v1_bundles__revision_id__artifacts__artifact_id__content_metadata_get",
    "requestMedia": [],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "GET /api/v1/bundles/{revision_id}/semantic-segments": {
    "method": "GET",
    "template": "/api/v1/bundles/{revision_id}/semantic-segments",
    "operationId": "bundle_semantic_api_v1_bundles__revision_id__semantic_segments_get",
    "requestMedia": [],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "POST /api/v1/bundles/{revision_id}/exports": {
    "method": "POST",
    "template": "/api/v1/bundles/{revision_id}/exports",
    "operationId": "bundle_export_api_v1_bundles__revision_id__exports_post",
    "requestMedia": [
      "application/json"
    ],
    "responseMedia": {
      "202": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "GET /api/v1/bundle-exports/{export_id}": {
    "method": "GET",
    "template": "/api/v1/bundle-exports/{export_id}",
    "operationId": "bundle_export_status_api_v1_bundle_exports__export_id__get",
    "requestMedia": [],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "GET /api/v1/bundle-exports/{export_id}/content": {
    "method": "GET",
    "template": "/api/v1/bundle-exports/{export_id}/content",
    "operationId": "bundle_export_content_api_v1_bundle_exports__export_id__content_get",
    "requestMedia": [],
    "responseMedia": {
      "200": [
        "application/zip"
      ],
      "206": [
        "application/zip",
        "multipart/byteranges"
      ],
      "304": [],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "416": [
        "text/plain"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "GET /api/v1/bundle-exports/{export_id}/content/metadata": {
    "method": "GET",
    "template": "/api/v1/bundle-exports/{export_id}/content/metadata",
    "operationId": "bundle_export_metadata_api_v1_bundle_exports__export_id__content_metadata_get",
    "requestMedia": [],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "POST /api/v1/bundles/{revision_id}/grants": {
    "method": "POST",
    "template": "/api/v1/bundles/{revision_id}/grants",
    "operationId": "bundle_grant_api_v1_bundles__revision_id__grants_post",
    "requestMedia": [
      "application/json"
    ],
    "responseMedia": {
      "201": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "POST /api/v1/bundle-grants/{grant_id}/revoke": {
    "method": "POST",
    "template": "/api/v1/bundle-grants/{grant_id}/revoke",
    "operationId": "bundle_revoke_api_v1_bundle_grants__grant_id__revoke_post",
    "requestMedia": [],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "POST /api/v1/bundle-imports": {
    "method": "POST",
    "template": "/api/v1/bundle-imports",
    "operationId": "bundle_import_api_v1_bundle_imports_post",
    "requestMedia": [
      "application/json"
    ],
    "responseMedia": {
      "201": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "GET /api/v1/bundle-imports/{import_id}": {
    "method": "GET",
    "template": "/api/v1/bundle-imports/{import_id}",
    "operationId": "bundle_import_get_api_v1_bundle_imports__import_id__get",
    "requestMedia": [],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "GET /api/v1/bundle-imports/{import_id}/manifest": {
    "method": "GET",
    "template": "/api/v1/bundle-imports/{import_id}/manifest",
    "operationId": "bundle_import_manifest_api_v1_bundle_imports__import_id__manifest_get",
    "requestMedia": [],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "206": [
        "application/json",
        "multipart/byteranges"
      ],
      "304": [],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "416": [
        "text/plain"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "GET /api/v1/bundle-imports/{import_id}/manifest/metadata": {
    "method": "GET",
    "template": "/api/v1/bundle-imports/{import_id}/manifest/metadata",
    "operationId": "bundle_import_manifest_metadata_api_v1_bundle_imports__import_id__manifest_metadata_get",
    "requestMedia": [],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "GET /api/v1/bundle-imports/{import_id}/artifacts/{artifact_id}/content": {
    "method": "GET",
    "template": "/api/v1/bundle-imports/{import_id}/artifacts/{artifact_id}/content",
    "operationId": "bundle_import_content_api_v1_bundle_imports__import_id__artifacts__artifact_id__content_get",
    "requestMedia": [],
    "responseMedia": {
      "200": [
        "*/*"
      ],
      "206": [
        "*/*",
        "multipart/byteranges"
      ],
      "304": [],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "416": [
        "text/plain"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "GET /api/v1/bundle-imports/{import_id}/artifacts/{artifact_id}/content/metadata": {
    "method": "GET",
    "template": "/api/v1/bundle-imports/{import_id}/artifacts/{artifact_id}/content/metadata",
    "operationId": "bundle_import_artifact_metadata_api_v1_bundle_imports__import_id__artifacts__artifact_id__content_metadata_get",
    "requestMedia": [],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "POST /api/v1/bundle-imports/{import_id}/exports": {
    "method": "POST",
    "template": "/api/v1/bundle-imports/{import_id}/exports",
    "operationId": "bundle_import_export_api_v1_bundle_imports__import_id__exports_post",
    "requestMedia": [
      "application/json"
    ],
    "responseMedia": {
      "202": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "POST /api/v1/local-copy-input-scopes/preview": {
    "method": "POST",
    "template": "/api/v1/local-copy-input-scopes/preview",
    "operationId": "local_copy_scope_preview_api_v1_local_copy_input_scopes_preview_post",
    "requestMedia": [
      "application/json"
    ],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "POST /api/v1/local-copy-input-scopes/install": {
    "method": "POST",
    "template": "/api/v1/local-copy-input-scopes/install",
    "operationId": "local_copy_scope_install_api_v1_local_copy_input_scopes_install_post",
    "requestMedia": [
      "application/json"
    ],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "POST /api/v1/local-copy-input-scopes/select": {
    "method": "POST",
    "template": "/api/v1/local-copy-input-scopes/select",
    "operationId": "local_copy_scope_select_api_v1_local_copy_input_scopes_select_post",
    "requestMedia": [
      "application/json"
    ],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "POST /api/v1/local-copy-input-scopes/revoke": {
    "method": "POST",
    "template": "/api/v1/local-copy-input-scopes/revoke",
    "operationId": "local_copy_scope_revoke_api_v1_local_copy_input_scopes_revoke_post",
    "requestMedia": [
      "application/json"
    ],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "GET /api/v1/local-copy-input-scopes/{scope_id}/revisions/{revision}": {
    "method": "GET",
    "template": "/api/v1/local-copy-input-scopes/{scope_id}/revisions/{revision}",
    "operationId": "local_copy_scope_get_api_v1_local_copy_input_scopes__scope_id__revisions__revision__get",
    "requestMedia": [],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  },
  "POST /api/v1/local-copy-input-scopes/bind-request": {
    "method": "POST",
    "template": "/api/v1/local-copy-input-scopes/bind-request",
    "operationId": "local_copy_scope_bind_api_v1_local_copy_input_scopes_bind_request_post",
    "requestMedia": [
      "application/json"
    ],
    "responseMedia": {
      "200": [
        "application/json"
      ],
      "400": [
        "text/plain",
        "application/json"
      ],
      "401": [
        "application/json"
      ],
      "403": [
        "application/json"
      ],
      "404": [
        "application/json"
      ],
      "409": [
        "application/json"
      ],
      "413": [
        "application/json"
      ],
      "415": [
        "application/json"
      ],
      "422": [
        "application/json"
      ],
      "503": [
        "application/json"
      ]
    }
  }
} as const;
export type RouteKey = keyof typeof ROUTES;
