import json
import urllib.request

import websocket


class OperaMonitor:

    DEBUG_URL = "http://localhost:9222/json/version"

    def get_websocket_url(self):
        with urllib.request.urlopen(self.DEBUG_URL) as response:
            data = json.loads(
                response.read().decode()
            )

        return data["webSocketDebuggerUrl"]

    def get_targets(self):

        websocket_url = self.get_websocket_url()

        ws = websocket.create_connection(
            websocket_url,
            origin="http://localhost:9222"
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

        return response["result"]["targetInfos"]

    def get_pages(self):

        targets = self.get_targets()

        pages = []

        for target in targets:

            if target.get("type") != "page":
                continue

            title = target.get("title", "")
            url = target.get("url", "")

            if not url:
                continue

            pages.append({
                "title": title,
                "url": url
            })

        return pages


if __name__ == "__main__":

    monitor = OperaMonitor()

    pages = monitor.get_pages()

    print("\n--- OPERA PAGES ---")

    for page in pages:

        print(
            f"Title: {page['title']}"
        )

        print(
            f"URL: {page['url']}"
        )

        print()