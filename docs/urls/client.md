# Client URLs Documentation

<!-- This file is auto-generated. To regenerate, run: python scripts/generate_url_docs.py -->

### All Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/all/` | `client_rest_views.ClientListAllRestView` | `clients:client_list_all_rest` | REST view for listing all clients. |

### Create Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/create/` | `client_rest_views.ClientCreateRestView` | `clients:client_create_rest` | REST view for creating new clients. |

### Jobs Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/<uuid:client_id>/jobs/` | `client_rest_views.ClientJobsRestView` | `clients:client_jobs_rest` | REST view for fetching all jobs for a specific client. |
| `/jobs/<uuid:job_id>/contact/` | `client_rest_views.JobContactRestView` | `clients:job_contact_rest` | REST view for contact information operations for a job. |

### Other
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/<uuid:client_id>/` | `client_rest_views.ClientRetrieveRestView` | `clients:client_retrieve_rest` | REST view for retrieving a specific client by ID. |

### Search Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/search/` | `client_rest_views.ClientSearchRestView` | `clients:client_search_rest` | REST view for client search. |

### Update Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/<uuid:client_id>/update/` | `client_rest_views.ClientUpdateRestView` | `clients:client_update_rest` | REST view for updating client information. |
