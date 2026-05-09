import os
import multiprocessing

bind = f'0.0.0.0:{os.environ.get("PORT", 8000)}'
workers = int(os.environ.get('WEB_CONCURRENCY', multiprocessing.cpu_count() * 2 + 1))
worker_class = 'sync'
timeout = 120
accesslog = '-'
errorlog = '-'
