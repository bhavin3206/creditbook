# import os
# from celery import Celery

# # Set default Django settings
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

# app = Celery("app")

# # Load task modules from all registered Django app configs.
# app.config_from_object("django.conf:settings", namespace="CELERY")

# # Auto-discover tasks in all apps
# app.autodiscover_tasks()
