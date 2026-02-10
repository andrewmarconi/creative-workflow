"""
Shared pytest fixtures and configuration for tvspots tests.
"""

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def admin_user(db):
    """Create an admin user for testing admin actions."""
    return User.objects.create_superuser(
        username="admin",
        email="admin@test.com",
        password="testpass123"
    )


@pytest.fixture
def staff_user(db):
    """Create a staff user for testing."""
    return User.objects.create_user(
        username="staff",
        email="staff@test.com",
        password="testpass123",
        is_staff=True
    )
