"""local_http connector: the only connector this local implementation needs.

Routine B is triggered over HTTP on localhost using a bearer token. No
external network service is required.
"""

import json
import os


def build_trigger_url(config):
    b = config["b_api"]
    return "http://{host}:{port}{path}".format(**b)


def auth_header(token):
    return {"Authorization": "Bearer " + token}


def load_token(secrets_dir):
    p = os.path.join(secrets_dir, "b_token.txt")
    with open(p, "r") as f:
        return f.read().strip()
