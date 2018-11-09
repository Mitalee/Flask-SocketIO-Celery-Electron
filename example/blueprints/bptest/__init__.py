from flask import Blueprint
#from example.app import create_celery_app

bptest = Blueprint('bptest', __name__)

from . import views, tasks