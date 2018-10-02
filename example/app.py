#!/usr/bin/env python
from threading import Lock
from flask import Flask, render_template, session, request, jsonify, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room, \
    close_room, rooms, disconnect
from flask_login import LoginManager, UserMixin, current_user, login_user, \
    logout_user

from flask_session import Session

from celery import Celery
import time
# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
app.config['SESSION_TYPE'] = 'filesystem'
socketio = SocketIO(app, async_mode=async_mode, message_queue='redis://localhost:6379/0')
login = LoginManager(app)
Session(app)
thread = None
thread_lock = Lock()

# Celery configuration
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'


# Initialize Celery
celery = Celery(app.name, broker=app.config.get('CELERY_BROKER_URL'))
celery.conf.update(app.config)

class User(UserMixin, object):
    def __init__(self, id=None):
        print('in class User: ', id)
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
         {'data': message['data'], 'count': 'from_server'+str(session['receive_count'])})

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
    print('in disconnect_request')
    emit('local_response',
         {'data': 'Disconnected!', 'count': session['receive_count']})
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

@celery.task(bind=False)
def long_task():
    for i in range(5):
        d = 'number'+str(i)
        socketio.emit('local_response',
         {'data': d, 'count': '0901'}, namespace='/test_local', room='abc')
        time.sleep(2)

@app.route('/longtask', methods=['POST'])
def longtask():
    task = long_task.apply_async()
    return jsonify({}), 202, {'Location':'xyz'}

if __name__ == '__main__':
    socketio.run(app, debug=True)
