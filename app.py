import json
from typing import TypedDict

from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, send, emit

app = Flask(__name__)
app.config['secret_key'] = 'superSecret!'
app.debug = True
socketio = SocketIO(app)


class Client(TypedDict):
    id: str
    okta_user_id: str
    name: str
    initiator: bool


order_list: dict[int, [Client]] = {}
client_list: list[Client] = []


@app.route('/', defaults={'name': 'Jan', 'order_number': 100})
@app.route('/<string:name>', defaults={'order_number': 100})
@app.route('/<string:name>/<int:order_number>')
def index(name: str, order_number: int):  # put application's code here
    return render_template('index.html', name=name, order_number=order_number)


if __name__ == '__main__':
    # app.run()
    socketio.run(app)


@socketio.on('message')
def handle_message(data):
    print(f'message: {data}')


@socketio.on('visit_order')
def check_order(data):
    global order_list
    global client_list
    order = data['order_number']
    order_being_looked_at = order in order_list
    client = Client(id=request.sid, okta_user_id="", name=data['user_name'], initiator=False)
    if not check_user_in_user_list(client['name']):
        client_list.append(client)

    if order_being_looked_at:
        initiator = get_order_initiator(order)
        if not check_user_is_in_order(client, order):
            order_list[order].append(client)

        # Let's send this user a headsup to ask wether they want to take over the current initiator.

        emit('take_over_possible', {"current_client": initiator['name']})
    else:
        # Order is not being looked at. Let's create a new entry and set this client as the initiator.
        # This makes sure that this client is the one which will receive the message that they have
        # been taken over if required.
        client['initiator'] = True
        order_list[order] = [client]



@socketio.on('take_over_request')
def take_over_request(data):
    global client_list
    order_number = data['data']
    order_initiator = get_order_initiator(order_number)
    client = get_current_client()
    emit('take_over_request', {"client": client}, room=order_initiator['id'])


def check_user_is_in_order(client: Client, room: int) -> bool:
    global order_list
    return bool([c for c in order_list[room] if c['name'] == client['name']])


def check_user_in_user_list(name: str) -> Client | None:
    global client_list
    # This should in theory only return one single Client.
    client = [c for c in client_list if c['name'] == name]
    return client if client else None


def get_order_initiator(order: int) -> Client:
    global order_list
    # This should in theory only return one single Client.

    return next(iter([c for c in order_list[order] if c['initiator']]))


def get_current_client() -> Client:
    global client_list
    return [c for c in client_list if c['id'] == request.sid][0]
