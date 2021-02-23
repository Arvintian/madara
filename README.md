# Madara

## Introduction

Madara is a python web framework for building APIs inspire by [flask](https://github.com/pallets/flask), but no [context](https://flask.palletsprojects.com/en/1.1.x/appcontext/) design. In addition added django like [middleware](https://docs.djangoproject.com/en/3.1/topics/http/middleware/) support.

## Installation

```

pip install -U madara

```

## Quickstart

```

from madara.app import Madara
from madara.wrappers import Request
from madara.blueprints import Blueprint

app = Madara(config={
    "debug": True,
    "middlewares": [
        "tests.middleware.M1",
        "tests.middleware.M2",
    ]
})


bp_example = Blueprint("bp_example")


@app.route("/error", methods=["GET"])
def app_error(request: Request):
    raise Exception("test except")


@app.route("/item/<int:the_id>", methods=["GET"])
def app_route(request: Request, the_id):
    return "item id is {}".format(the_id)


@bp_example.route("/item", methods=["POST"])
def blueprint_route(request: Request):
    data = request.get_json()
    return {
        "code": 0,
        "result": data,
    }


app.register_blueprint(bp_example, url_prefix="/blueprint")

if __name__ == "__main__":
    app.run()

```