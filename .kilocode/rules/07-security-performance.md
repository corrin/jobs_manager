# Security and Performance

## Authentication and Authorization Security

### JWT Authentication

```python
# settings.py (relevant excerpt)
from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "VERIFYING_KEY": None,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIMS": "token_type",
    "AUTH_COOKIE": "access_token",
    "AUTH_COOKIE_SECURE": use_secure_cookies(),  # Secure cookies in production/tunnel
    "AUTH_COOKIE_HTTP_ONLY": True,
    "AUTH_COOKIE_SAMESITE": "Lax",
    "AUTH_COOKIE_DOMAIN": get_cookie_domain(),    # Cross-subdomain sharing
    "REFRESH_COOKIE": "refresh_token",
    "REFRESH_COOKIE_SECURE": use_secure_cookies(),
    "REFRESH_COOKIE_HTTP_ONLY": True,
    "REFRESH_COOKIE_SAMESITE": "Lax",
}
```

- Uses secure cookies (`Secure`, `HttpOnly`, `SameSite=Lax`) and dynamic domain for tunnel/prod environments.
- Allows refresh token rotation and blacklist after rotation.
- Access token lifetime: 8h; refresh token: 1 day.
- Dynamic configuration based on environment variables for maximum security.

## Performance Optimization

### Query Optimization

```python
# apps/job/managers.py
from django.db import models
from django.db.models import Prefetch, Count, Sum, Avg

class OptimizedJobManager(models.Manager):
    """Optimized manager for Job queries."""
    def with_related_data(self):
        """Load related data in an optimized way."""
        return self.select_related(
            'client',
            'created_by'
        ).prefetch_related(
            'people',
            'cost_sets__cost_lines',
            'events'
        )
    def with_cost_summary(self):
        """Annotate with calculated cost summary."""
        return self.annotate(
            total_cost_lines=Count('cost_sets__cost_lines'),
            estimated_total=Sum(
                'cost_sets__cost_lines__total',
                filter=models.Q(cost_sets__kind='estimate')
            ),
            actual_total=Sum(
                'cost_sets__cost_lines__total',
                filter=models.Q(cost_sets__kind='actual')
            ),
            avg_hourly_rate=Avg(
                'cost_sets__cost_lines__rate',
                filter=models.Q(cost_sets__cost_lines__kind='time')
            )
        )
    def active_with_recent_activity(self):
        """Active jobs with recent activity."""
        from django.utils import timezone
        from datetime import timedelta
        recent_date = timezone.now() - timedelta(days=30)
        return self.filter(
            status__in=['approved', 'in_progress'],
            updated_at__gte=recent_date
        ).with_related_data().with_cost_summary()

class OptimizedCostSetQuerySet(models.QuerySet):
    """Optimized QuerySet for CostSet."""
    def with_lines_and_totals(self):
        """Load lines and calculate totals."""
        return self.prefetch_related(
            Prefetch(
                'cost_lines',
                queryset=CostLine.objects.select_related().order_by('created_at')
            )
        ).annotate(
            lines_count=Count('cost_lines'),
            calculated_total=Sum('cost_lines__total')
        )
    def latest_by_kind(self):
        """Get the latest CostSet of each type per job."""
        return self.order_by('job', 'kind', '-created_at').distinct('job', 'kind')
```

## Related References

- See: [01-architecture-design-patterns.md](./01-architecture-design-patterns.md)
- See: [04-data-handling-persistence.md](./04-data-handling-persistence.md)
- See: [05-error-management-logging.md](./05-error-management-logging.md)
- See: [06-testing-quality-assurance.md](./06-testing-quality-assurance.md)
