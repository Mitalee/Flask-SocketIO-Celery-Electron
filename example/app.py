#!/usr/bin/env python
from threading import Lock
from flask import Flask, render_template, session, request, jsonify, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room, \
    close_room, rooms, disconnect
from flask_login import LoginManager, UserMixin, current_user, login_user, \
    logout_user

from flask_session import Session

from celery import Celery

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
app.config['SESSION_TYPE'] = 'filesystem'
#socketio = SocketIO(app, async_mode=async_mode, message_queue='redis://localhost:6379/0')

login = LoginManager(app)
Session(app)
thread = None
thread_lock = Lock()

# Celery configuration
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

CELERY_TASK_LIST = [
    'tasks',
]

 # for socketio
import eventlet
eventlet.monkey_patch()
socketio = SocketIO(app, logger=True, engineio_logger=True, async_mode='eventlet', message_queue=app.config['CELERY_BROKER_URL'])

# Initialize Celery
celery = Celery(app.name, broker=app.config.get('CELERY_BROKER_URL'), include=CELERY_TASK_LIST)
celery.conf.update(app.config)

class User(UserMixin, object):
    def __init__(self, id=None):
        self.id = id

def background_thread():
    """Example of how to send server generated events to clients."""
    count = 0
    while True:
        socketio.sleep(10)
        count += 1
        socketio.emit('local_response',
                      {'data': 'Server generated event', 'count': count},
                      namespace='/test_local')


@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)

@login.user_loader
def load_user(id):
    return User(id)

@app.route('/session', methods=['GET', 'POST'])
def session_access():
    if request.method == 'GET':
        return jsonify({
            'session': session.get('value', 'null'),
            'user': current_user.id
                if current_user.is_authenticated else 'anonymous'
        })
    data = request.get_json()
    if 'session' in data:
        session['value'] = data['session']
    elif 'user' in data:
        if data['user']:
            login_user(User(data['user']))
            print('current user is: ', current_user)
            return jsonify({
            'sessionid': session.sid,
            'user': current_user.id
                if current_user.is_authenticated else 'anonymous'
        })
        else:
            logout_user()
            return jsonify({
            'sessionid': session.sid,
            'user': current_user.id
                if current_user.is_authenticated else 'anonymous'
        })
    return 'dunno', 204


#@socketio.on('web_to_local_event', namespace='/test_web')
@app.route('/web2local', methods=['GET','POST'])
def test_web_to_local_message():
    data = request.get_json()
    print('in web2local event: ', data['message'])
    print('in web2local function')
    session['receive_count'] = session.get('receive_count', 0) + 1 
    emit('local_response',
         {'data': data['message'], 'count': session['receive_count']}, namespace='/test_local', room=current_user.id)
    return jsonify({'result': 'ok'})


@socketio.on('local_event', namespace='/test_local')
def test_local_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    print('in local_event: ', message)
    emit('local_response',
         {'data': message['data'], 'count': session['receive_count']})

@socketio.on('local_to_web_event', namespace='/test_local')
def test_local_to_web_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    print('in local2web event: ', message)
    emit('web_response',
         {'data': message['data'], 'count': session['receive_count']}, namespace='/test_web')

# @socketio.on('local_to_web_event', namespace='/test_local')
# def test_local_to_web_message(message):
#     session['receive_count'] = session.get('receive_count', 0) + 1
#     print('in local2web event: ', message)
#     emit('web_response',
#          {'data': message['data'], 'count': session['receive_count']}, namespace='/test_web')

#To disconnect the desktop local client
@socketio.on('disconnect_request', namespace='/test_local')
def local_disconnect_request():
    session['receive_count'] = session.get('receive_count', 0) + 1
    #print('in disconnect_request')
    emit('local_response',
         {'data': 'Disconnected!', 'count': session['receive_count']})
    socketio.sleep(0)
    print('emitted from disconnect')
    disconnect()


@socketio.on('disconnect', namespace='/test_local')
def test_local_disconnect():
    print('Client disconnected', request.sid)

#To allow desktop local client to access the user session (currently by username)
@socketio.on('join', namespace='/test_local')
def join(message):
    join_room(message['room'])
    print('in join function app.y, joined: ', message['room'])
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('local_response',
         {'data': 'In rooms: ' + ', '.join(rooms()),
          'count': session['receive_count']})

@socketio.on('leave', namespace='/test_local')
def leave(message):
    leave_room(message['room'])
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('local_response',
         {'data': 'In rooms: ' + ', '.join(rooms()),
          'count': session['receive_count']})

@app.route('/longtask', methods=['POST'])
def longtask():
    print('IN LONGTASK WITH USER_ID: ', current_user.id)
    from tasks import long_background_task
    task = long_background_task.delay(user_id=current_user.id)
    return jsonify({}), 202, {'Location': url_for('taskstatus',
                                                  task_id=task.id)}

# @celery.task(bind=True)
# def long_task(self, user_id):
#     """Background task that runs a long function with progress reports."""
#     verb = ['Starting up', 'Booting', 'Repairing', 'Loading', 'Checking']
#     adjective = ['master', 'radiant', 'silent', 'harmonic', 'fast']
#     noun = ['solar array', 'particle reshaper', 'cosmic ray', 'orbiter', 'bit']
#     message = ''
#     total = random.randint(10, 50)
#     for i in range(total):
#         if not message or random.random() < 0.25:
#             message = '{0} {1} {2}...'.format(random.choice(verb),
#                                               random.choice(adjective),
#                                               random.choice(noun))
#         self.update_state(state='PROGRESS',
#                           meta={'current': i, 'total': total,
#                                 'status': message})
#         time.sleep(1)
#     return {'current': 100, 'total': 100, 'status': 'Task completed!',
#             'result': 42}

# @app.route('/longtask', methods=['POST'])
# def longtask():
#     task = long_task.apply_async()
#     return jsonify({}), 202, {'Location': url_for('taskstatus',
#                                                   task_id=task.id)}


@app.route('/status/<task_id>')
def taskstatus(task_id):
    from tasks import long_background_task
    task = long_background_task.AsyncResult(task_id)
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'current': 0,
            'total': 1,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 1),
            'status': task.info.get('status', '')
        }
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        # something went wrong in the background job
        response = {
            'state': task.state,
            'current': 1,
            'total': 1,
            'status': str(task.info),  # this is the exception raised
        }
    return jsonify(response)


if __name__ == '__main__':
    socketio.run(app, debug=True)
