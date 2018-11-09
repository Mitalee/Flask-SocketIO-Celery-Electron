
from . import bptest
from example.app import create_celery_app

celery = create_celery_app()

@bptest.route('/SendTallyFunc/', methods=['GET','POST'])
def send_room_message_without_socketio():
        from .tasks import test_tally_celery
        print('SENDING TO CELERY')
        tasks = test_tally_celery.delay()
        return ('Processing.. please wait..')