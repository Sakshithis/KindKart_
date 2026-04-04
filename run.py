import eventlet
eventlet.monkey_patch()

from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    # host='0.0.0.0' allows other students on the same Wi-Fi to access the app
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
