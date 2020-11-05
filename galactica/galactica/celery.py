from __future__ import absolute_import
import os
from celery import Celery
from django.conf import settings
from celery.schedules import crontab

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'galactica.settings')
app = Celery('galactica')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))


# scheduling the syncing task every 2 hours
app.conf.beat_schedule = {
    "sync-with-swapi-endpoint": {
        "task": "sync_with_swapi_endpoint",
        "schedule": crontab(minute="0", hour="*/2", day_of_month="*", month_of_year="*", day_of_week="*")
    }
}