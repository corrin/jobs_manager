from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "User Accounts"

    def ready(self) -> None:
        # Import to register DRF Spectacular authentication extensions
        import jobs_manager.extensions  # noqa: F401
