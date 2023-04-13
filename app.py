from typing import TypedDict

from flask import Flask, render_template, request, session
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'superSecret!'
app.debug = True
socketio = SocketIO(app)


class Client(TypedDict):
    id: str
    okta_user_id: str
    name: str
    initiator: bool
    order_number: int


client_list: list[Client] = []


@app.route('/', defaults={'name': 'Jan', 'order_number': 100})
@app.route('/<string:name>', defaults={'order_number': 100})
@app.route('/<string:name>/<int:order_number>')
def index(name: str, order_number: int):  # put application's code here.
    session['name'] = name
    session['order_number'] = order_number
    return render_template('index.html', name=name, order_number=order_number)


if __name__ == '__main__':
    # app.run()
    socketio.run(app)


@socketio.on('visit_order')
def check_order(data):
    global client_list
    order = session['order_number']
    client = bake_client()
    initiator = get_order_initiator(order)
    if initiator:
        if not check_user_in_user_list(client['name']):
            client_list.append(client)

        if initiator['name'] != client['name']:
            emit('take_over_possible', {"current_client": initiator['name']})
    else:
        client['initiator'] = True
        client_list.append(client)
    print(client_list)


@socketio.on('take_over_request')
def take_over_request(data):
    global client_list
    order_number = session['order_number']
    initiator = get_order_initiator(order_number)
    print(initiator, 'initiator')
    client = get_client(session['name'])
    emit('take_over_request', {"client": client}, room=initiator['id'])


@socketio.on('take_over_accept')
def take_over_accept(data):
    global client_list
    client = data['data']
    get_client(client['name'])['initiator'] = True
    initiator = get_order_initiator(session['order_number'])
    initiator['initiator'] = False

    # Send headsup to overtaker
    emit('take_over_completed', client, room=get_client(client['name'])['id'])

    # Send headsup to OG initiator
    print(get_client(session['name']), 'dingetje')
    emit('take_over_completed', client, room=get_client(session['name'])['id'])


def check_user_in_user_list(name: str) -> Client | None:
    global client_list
    # This should in theory only return one single Client.
    client = [c for c in client_list if c['name'] == name]
    return client if client else None


def get_order_initiator(order: int) -> Client | None:
    global client_list
    clients = [c for c in client_list if c['order_number'] == order and c['initiator']]
    if clients:
        return clients[0]
    else:
        return False


def get_client(name: str) -> Client:
    global client_list
    return [c for c in client_list if c['name'] == name][0]


def bake_client() -> Client:
    client = [c for c in client_list if c['name'] == session['name']]
    if client:
        client[0]['id'] = request.sid
        return client[0]
    else:
        return Client(
            id=request.sid,
            okta_user_id='',
            name=session['name'],
            initiator=False,
            order_number=session['order_number']
        )
