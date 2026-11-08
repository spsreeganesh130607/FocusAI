import json
import urllib.request

import websocket


def get_browser_websocket():

    url = "http://localhost:9222/json/version"

    with urllib.request.urlopen(url) as response:

        data = json.loads(
            response.read().decode()
        )

    return data["webSocketDebuggerUrl"]


def get_targets():

    websocket_url = get_browser_websocket()

    ws = websocket.create_connection(
        websocket_url
    )

    command = {
        "id": 1,
        "method": "Target.getTargets"
    }

    ws.send(json.dumps(command))

    response = json.loads(
        ws.recv()
    )

    ws.close()

    return response


if __name__ == "__main__":

    result = get_targets()

    print(json.dumps(
        result,
        indent=4
    ))
    