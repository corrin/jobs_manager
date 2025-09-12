# Workflow URLs Documentation

<!-- This file is auto-generated. To regenerate, run: python scripts/generate_url_docs.py -->

## API Endpoints

#### Aws Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/aws/instance/` | `aws_instance_view.AWSInstanceManagementView` | `aws_instance_management` | Combined view for AWS instance management operations |
| `/api/aws/instance/reboot/` | `aws_instance_view.reboot_instance` | `aws_instance_reboot` | Reboot the UAT instance |
| `/api/aws/instance/start/` | `aws_instance_view.start_instance` | `aws_instance_start` | Start the UAT instance |
| `/api/aws/instance/status/` | `aws_instance_view.get_instance_status` | `aws_instance_status` | Get current status of the UAT instance |
| `/api/aws/instance/stop/` | `aws_instance_view.stop_instance` | `aws_instance_stop` | Stop the UAT instance |

#### System
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/company-defaults/` | `company_defaults_api.CompanyDefaultsAPIView` | `api_company_defaults` | API view for managing company default settings. |
| `/api/enums/<str:enum_name>/` | `get_enum_choices` | `get_enum_choices` | API endpoint to get enum choices. |

#### Xero Integration
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/xero/authenticate/` | `xero_view.xero_authenticate` | `api_xero_authenticate` | Xero Authentication (Step 1: Redirect user to Xero OAuth2 login) |
| `/api/xero/create_invoice/<uuid:job_id>/` | `xero_view.create_xero_invoice` | `create_invoice` | Creates an Invoice in Xero for a given job. |
| `/api/xero/create_purchase_order/<uuid:purchase_order_id>/` | `xero_view.create_xero_purchase_order` | `create_xero_purchase_order` | Creates or updates a Purchase Order in Xero for a given purchase order. |
| `/api/xero/create_quote/<uuid:job_id>/` | `xero_view.create_xero_quote` | `create_quote` | Creates a quote in Xero for a given job. |
| `/api/xero/delete_invoice/<uuid:job_id>/` | `xero_view.delete_xero_invoice` | `delete_invoice` | Deletes a specific invoice in Xero for a given job, identified by its Xero ID. |
| `/api/xero/delete_purchase_order/<uuid:purchase_order_id>/` | `xero_view.delete_xero_purchase_order` | `delete_xero_purchase_order` | Deletes a Purchase Order in Xero. |
| `/api/xero/delete_quote/<uuid:job_id>/` | `xero_view.delete_xero_quote` | `delete_quote` | Deletes a quote in Xero for a given job. |
| `/api/xero/disconnect/` | `xero_view.xero_disconnect` | `xero_disconnect` | Disconnects from Xero by clearing the token from cache and database. |
| `/api/xero/oauth/callback/` | `xero_view.xero_oauth_callback` | `xero_oauth_callback` | OAuth callback |
| `/api/xero/ping/` | `xero_view.xero_ping` | `xero_ping` | Simple endpoint to check if the user is authenticated with Xero. |
| `/api/xero/sync-info/` | `xero_view.get_xero_sync_info` | `xero_sync_info` | Get current sync status and last sync times, including Xero Items/Stock. |
| `/api/xero/sync-stream/` | `xero_view.stream_xero_sync` | `stream_xero_sync` | HTTP endpoint to serve an EventSource stream of Xero sync events. |
| `/api/xero/sync/` | `xero_view.start_xero_sync` | `synchronise_xero_data` | View function to start a Xero sync as a background task. |
| `/api/xero/webhook/` | `XeroWebhookView` | `xero_webhook` | Handle incoming Xero webhook notifications. |

### App-Errors Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/app-errors/` | `app_error_view.AppErrorListAPIView` | `app-error-list` | API view for listing application errors. |
| `/app-errors/<uuid:pk>/` | `app_error_view.AppErrorDetailAPIView` | `app-error-detail` | API view for retrieving a single application error. |

### System
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/xero-errors/` | `xero_view.XeroErrorListAPIView` | `xero-error-list` | API view for listing Xero synchronization errors. |
| `/xero-errors/<uuid:pk>/` | `xero_view.XeroErrorDetailAPIView` | `xero-error-detail` | API view for retrieving a single Xero synchronization error. |

### Xero Integration
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/xero/` | `xero_view.XeroIndexView` | `xero_index` | Note this page is currently inaccessible. We are using a dropdown menu instead. |
| `/xero/sync-progress/` | `xero_view.xero_sync_progress_page` | `xero_sync_progress` | Render the Xero sync progress page. |
