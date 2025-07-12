# Client URLs Documentation

<!-- This file is auto-generated. To regenerate, run: python scripts/generate_url_docs.py -->

### All Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/all/` | `client_rest_views.ClientListAllRestView` | `clients:client_list_all_rest` | REST view for listing all clients. |

### Contacts Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/<uuid:client_id>/contacts/` | `client_rest_views.ClientContactsRestView` | `clients:client_contacts_rest` | REST view for fetching contacts of a client. |
| `/contacts/` | `client_rest_views.ClientContactCreateRestView` | `clients:client_contact_create_rest` | REST view for creating client contacts. |

### Create Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/create/` | `client_rest_views.ClientCreateRestView` | `clients:client_create_rest` | REST view for creating new clients. |

### Search Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/search/` | `client_rest_views.ClientSearchRestView` | `clients:client_search_rest` | REST view for client search. |
