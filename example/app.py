#!/usr/bin/env python
from threading import Lock
from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, emit, join_room, leave_room, \
    close_room, rooms, disconnect

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on installed packages.
async_mode = None

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock()


def background_thread():
    """Example of how to send server generated events to clients."""
    count = 0
    while True:
        socketio.sleep(10)
        count += 1
        socketio.emit('my_response',
                      {'data': 'Server generated event', 'count': count},
                      namespace='/test')


@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)


@socketio.on('web_event', namespace='/test_web')
def test_web_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    print('in web_event')
    emit('web_response',
         {'data': message['data'], 'count': session['receive_count']}, namespace='/test_web')

@socketio.on('web_to_local_event', namespace='/test_web')
def test_web_to_local_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    print('in web2local event')
    emit('local_response',
         {'data': message['data'], 'count': session['receive_count']}, namespace='/test_local')


@socketio.on('local_event', namespace='/test_local')
def test_local_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    print('in local_event')
    emit('local_response',
         {'data': message['data'], 'count': session['receive_count']}, namespace='/test_local')

@socketio.on('local_to_web_event', namespace='/test_local')
def test_local_to_web_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    print('in local2web event')
    emit('web_response',
         {'data': message['data'], 'count': session['receive_count']}, namespace='/test_web')


@socketio.on('disconnect_request', namespace='/test_web')
def web_disconnect_request():
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('web_response',
         {'data': 'Disconnected!', 'count': session['receive_count']})
    disconnect()

@socketio.on('disconnect_request', namespace='/test_local')
def local_disconnect_request():
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('local_response',
         {'data': 'Disconnected!', 'count': session['receive_count']})
    disconnect()

@socketio.on('my_web_ping', namespace='/test_web')
def ping_pong_web():
    emit('my_web_pong')

@socketio.on('my_local_ping', namespace='/test_local')
def ping_pong_local():
    emit('my_local_pong')


@socketio.on('connect', namespace='/test_web')
def test_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background_thread)
    emit('web_response', {'data': 'Connected', 'count': 0})


@socketio.on('disconnect', namespace='/test_web')
def test_web_disconnect():
    print('Client disconnected', request.sid)

@socketio.on('connect', namespace='/test_local')
def test_local_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background_thread)
    emit('local_response', {'data': 'Connected', 'count': 0})


@socketio.on('disconnect', namespace='/test_local')
def test_local_disconnect():
    print('Client disconnected', request.sid)



if __name__ == '__main__':
    socketio.run(app, debug=True)
