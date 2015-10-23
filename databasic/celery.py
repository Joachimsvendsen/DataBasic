from __future__ import absolute_import
import os
from celery import Celery
from databasic import settings

celery_app = Celery('databasic',
             broker=app.config['BROKER_URL'],
             backend=app.config['BACKEND_URL'],
             include=['databasic.tasks'])

# expire backend results in one hour
celery_app.conf.update(
    CELERY_TASK_RESULT_EXPIRES=3600,
)

if __name__ == '__main__':
    celery_app.start()