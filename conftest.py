import pytest


# Override static files storage for all tests so that templates using
# {% load static %} do not fail with "Missing staticfiles manifest entry".
@pytest.fixture(autouse=True)
def use_simple_static_storage(settings):
    settings.STORAGES = {
        **settings.STORAGES,
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'
        },
    }
