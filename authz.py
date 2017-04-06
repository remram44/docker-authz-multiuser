import base64
from flask import Flask, jsonify, request
import json
import re


application = app = Flask(__name__)
app.debug = True


# Keeps track of containers
# Key is ID, value should be the username of owner or something
# TODO: Replace with better data structure, ID might be abbreviated
containers = {}


def auth(data):
    uri = data['RequestUri']
    method = data['RequestMethod']
    if data['RequestUri'] == '/_ping':
        return True
    if not uri.startswith('/v1.27/'):
        app.logger.warning("Got request with unsupport API version: %s", uri)
        return "Unsupported API version"

    if method == 'GET' and (uri == '/v1.27/images/json' or uri.startswith('/v1.27/containers/json') or
                            uri == '/v1.27/info' or uri.startswith('/v1.27/events?')):
        # General information, allowed
        return True
    elif method == 'POST' and uri.startswith('/v1.27/images/create?'):
        # Pulling a new image, allowed
        return True
    elif method == 'POST' and uri == '/v1.27/containers/create':
        # TODO: Validate options
        body = json.loads(base64.b64decode(data['RequestBody']))

        if body['Image'] == 'hello-world':
            return True
        else:
            return "You may only run hello-world"
    elif re.match(r'/v1\.27/containers/[a-f0-9]+', uri):
        # Operation on a container
        if containers.get(uri[18:18+64]):
            return True
        else:
            return "You don't have access to this container"

    app.logger.debug("Unhandled request: %s %s", method, uri)
    return False


@app.route("/Plugin.Activate", methods=['POST'])
def activate():
    return jsonify({'Implements': ['authz']})


@app.route("/AuthZPlugin.AuthZReq", methods=['POST'])
def authz_request():
    plugin_request = json.loads(request.data)
    app.logger.info("request: %r", plugin_request)
    response = auth(plugin_request)

    if response is False:
        response = {"Allow": False,
                    "Msg":   "Internal error",
                    "Err":   "Internal error"}
    elif response is True:
        response = {"Allow": True,
                    "Msg":   "success"}
    else:
        response = {"Allow": False,
                    "Msg":   response,
                    "Err":   response}

    return jsonify(**response)


@app.route("/AuthZPlugin.AuthZRes", methods=['POST'])
def authz_response():
    plugin_response = json.loads(request.data)
    app.logger.info("response: %r", plugin_response)
    uri = plugin_response['RequestUri']

    if uri == '/v1.27/containers/create':
        body = json.loads(base64.b64decode(plugin_response['ResponseBody']))
        if 'Id' in body:
            app.logger.info("Container created: %s", body['Id'])
            containers[body['Id']] = True

    return jsonify(Allow=True)


if __name__ == "__main__":
    app.run()
