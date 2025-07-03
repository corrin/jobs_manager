# Client URLs Documentation

<!-- This file is auto-generated. To regenerate, run: python scripts/generate_url_docs.py -->

## API Endpoints

#### Client Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/client/<uuid:client_id>/contacts/` | `client_views.get_client_contacts_api` | `clients:api_get_client_contacts` | API endpoint to retrieve all contacts for a specific client. |
| `/api/client/contact/` | `client_views.create_client_contact_api` | `clients:api_create_client_contact` | API endpoint to create a new contact for a client. |
| `/api/client/contact/<uuid:contact_id>/` | `client_views.client_contact_detail_api` | `clients:api_client_contact_detail` | API endpoint to retrieve, update, or delete a specific contact. |

### Add Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/add/` | `client_views.AddClient` | `clients:add_client` | View for adding new clients with Xero integration. |

### All Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/all/` | `client_rest_views.ClientListAllRestView` | `clients:clients_rest:client_list_all_rest` | REST view for listing all clients. |

### Contacts Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/<uuid:client_id>/contacts/` | `client_rest_views.ClientContactsRestView` | `clients:clients_rest:client_contacts_rest` | REST view for fetching contacts of a client. |
| `/contacts/` | `client_rest_views.ClientContactCreateRestView` | `clients:clients_rest:client_contact_create_rest` | REST view for creating client contacts. |

### Create Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/create/` | `client_rest_views.ClientCreateRestView` | `clients:clients_rest:client_create_rest` | REST view for creating new clients. |

### Other
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/` | `client_views.ClientListView` | `clients:list_clients` | View for displaying a list of all clients in a table format. |
| `/<uuid:pk>/` | `client_views.ClientUpdateView` | `clients:update_client` | context_object_name = "clients" |

### Search Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/search/` | `client_rest_views.ClientSearchRestView` | `clients:clients_rest:client_search_rest` | REST view for client search. |
