
from flask import Blueprint

from example.app import socketio, session

from flask_socketio import emit, join_room, leave_room, \
    close_room, rooms, disconnect

bptest2 = Blueprint('bptest2', __name__)

@bptest2.route('/SendTallyFunc2/', methods=['GET','POST'])
def send_room_message_without_socketio():
        from example.blueprints.bptest2.tasks import test_tally_celery
        task = test_tally_celery.delay()
        print ('SENDING TO CELERY. Please wait..')
        return(task.id)

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

@socketio.on('connect', namespace='/test_web2')
def test_connect():
    print('WEB CONNECTED ON OPEN AUTO')
    emit('web_response', {'data': 'Connected', 'count': 0})


@socketio.on('web_event', namespace='/test_web2')
def test_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('web_response',
         {'data': message['data'], 'count': session['receive_count']})

@socketio.on('disconnect_request', namespace='/test_web2')
def local_disconnect_request():
    session['receive_count'] = session.get('receive_count', 0) + 1
    #print('in disconnect_request')
    emit('lweb_response',
         {'data': 'Disconnected!', 'count': session['receive_count']})
    socketio.sleep(0)
    print('WEB DISCONNECTED ON CLOSE/REFRESH')
    disconnect()