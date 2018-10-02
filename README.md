# Flask-SocketIO-Celery-Electron
Multiplexed all of Miguel's SocketIO and Celery tuts. :)

Allowing a celery worker to emit websocket messages to an electron desktop app. I needed this to communicate with a silent Electron app that would sit in the system tray and simply relay messages back and forth to the server. a HTTP request on the frontend would communicate to the server the message it intended to send to the client.

Used a combination of namespaces and rooms to identify the desktop client.

CELERY:
$ source venv/bin/activate
(venv) $ celery worker -A app.celery --loglevel=info

REDIS:
./run-redis.sh

FLASK:
$ source venv/bin/activate
(venv) $ python app.py

![alt text](https://github.com/Mitalee/Flask-SocketIO-Celery-Electron/blob/master/Demo.png)


Miguel's Tutorials:
https://blog.miguelgrinberg.com/post/using-celery-with-flask
https://blog.miguelgrinberg.com/post/easy-websockets-with-flask-and-gevent/page/10

Flask-SocketIO documentation:
https://flask-socketio.readthedocs.io/en/latest/

Electron Links:
https://github.com/electron/electron-api-demos
