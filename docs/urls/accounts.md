# Accounts URLs Documentation

<!-- This file is auto-generated. To regenerate, run: python scripts/generate_url_docs.py -->

## API Endpoints

#### Staff Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/staff/` | `staff_api.StaffListCreateAPIView` | `accounts:api_staff_list_create` | API endpoint for listing and creating staff members. |
| `/api/staff/<uuid:pk>/` | `staff_api.StaffRetrieveUpdateDestroyAPIView` | `accounts:api_staff_detail` | API endpoint for retrieving, updating, and deleting individual staff members. |
| `/api/staff/all/` | `staff_views.StaffListAPIView` | `accounts:api_staff_list` | API endpoint for retrieving list of staff members for Kanban board. |
| `/api/staff/rates/<uuid:staff_id>/` | `staff_views.get_staff_rates` | `accounts:get_staff_rates` | Retrieve wage rates for a specific staff member. |

#### Token Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/api/token/` | `token_view.CustomTokenObtainPairView` | `accounts:token_obtain_pair` | Customized token obtain view that handles password reset requirement |
| `/api/token/refresh/` | `token_view.CustomTokenRefreshView` | `accounts:token_refresh` | Customized token refresh view that uses httpOnly cookies |

### Authentication
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/logout/` | `user_profile_view.logout_user` | `accounts:api_logout` | Custom logout view that clears JWT httpOnly cookies |

### Django Admin
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/([/]+)/history/([/]+)/` | `history_form_view` | `admin:accounts_staff_simple_history` | Display the historical form view for a specific object version. |
| `/<id>/password/` | `user_change_password` | `admin:auth_user_password_change` | Display the password change form for a specific user. |

### Me Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/me/` | `user_profile_view.get_current_user` | `accounts:get_current_user` | Get current authenticated user information via JWT from httpOnly cookie |

### Password_Change Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/password_change/` | `password_views.SecurityPasswordChangeView` | `accounts:password_change` | Custom password change view with enhanced security requirements. |

### Staff Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/staff/` | `staff_views.StaffListView` | `accounts:list_staff` | Display list of all staff members. |
| `/staff/<uuid:pk>/` | `staff_views.StaffUpdateView` | `accounts:update_staff` | Update existing staff member details. |
| `/staff/new/` | `staff_views.StaffCreateView` | `accounts:create_staff` | Create new staff member. |
