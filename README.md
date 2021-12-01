# Madara

## Introduction

Madara is a python web framework for building APIs inspire by [flask](https://github.com/pallets/flask), but no [context](https://flask.palletsprojects.com/en/1.1.x/appcontext/) design. In addition added [middleware](https://github.com/Arvintian/madara#middleware) mechanism.

Through the middleware mechanism, madara opened the plug-in door, link [koa](https://github.com/koajs/koa)'s design.

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

## User’s Guide

### Application

A minimal Madara application looks something like this:

```
from madara.app import Madara
app = Madara(config={})


@app.route('/')
def hello_world(request):
    return 'Hello, World!'


if __name__ == "__main__":
    app.run()
```

- First we imported the Madara class. An instance of this class will be our [WSGI application](https://www.python.org/dev/peps/pep-3333).
- Next we create an instance of this class.
- We then use the route() decorator to tell Madara what URL should trigger our function.
- Just save it as `hello.py`, to run the application you can just exec `python hello.py`.

### Routing

Use the route() decorator to bind a function to a URL.

```
@app.route('/')
def index(request):
    return 'Index Page'

@app.route('/hello')
def hello(request):
    return 'Hello, World'
```

You can add variable sections to a URL by marking sections with <variable_name>. Your function then receives the <variable_name> as a keyword argument. Optionally, you can use a converter to specify the type of the argument like <converter:variable_name>.

```
@app.route('/user/<username>')
def show_user_profile(request, username):
    # show the user profile for that user
    return 'User %s' % escape(username)

@app.route('/post/<int:post_id>')
def show_post(request, post_id):
    # show the post with the given id, the id is an integer
    return 'Post %d' % post_id
```

Converter types:

- `string` (default) accepts any text without a slash

- `int` accepts positive integers

- `float` accepts positive floating point values

- `path` like string but also accepts slashes

- `uuid` accepts UUID strings

Web applications use different HTTP methods when accessing URLs. You should familiarize yourself with the HTTP methods as you work with Madara. By default, a route only answers to GET requests. You can use the methods argument of the route() decorator to handle different HTTP methods.

```
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return do_the_login()
    else:
        return show_the_login_form()
```

### Request

For web applications it’s crucial to react to the data a client sends to the server. In Madara this information is provided by the first param `request` object to your function.

The madara request object just a warp of [werkzeug request](https://werkzeug.palletsprojects.com/en/1.0.x/wrappers/#werkzeug.wrappers.Request), so your can access request data by werkzeug's methods.

### Response

The return value from a view function is automatically converted into a [werkzeug response](https://werkzeug.palletsprojects.com/en/1.0.x/wrappers/#werkzeug.wrappers.Response) for you. If the return value is a dict, which will serialize any supported JSON data type and set mimetype to application/json.

### Blueprint

A Blueprint is a way to organize a group of related views and other code. Rather than registering views and other code directly with an application, they are registered with a blueprint.

```

from madara.app import Madara
from madara.blueprints import Blueprint

app = Madara(config={})

bp_example = Blueprint("bp_example")

@app.route('/')
def hello_world(request):
    return 'Hello, World!'


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

### Middleware

Middleware is a framework of hooks into Madara’s request/response processing. It’s a light, low-level “plugin” system for globally altering input or output.

```

class SimpleMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response

    def process_view(self, request, callback, callback_kwargs):
        return None

    def process_exception(self, request, exception):
        return None

```

The `get_response` callable provided by Madara might be the actual view (if this is the last listed middleware) or it might be the next middleware in the chain.

`process_view()` is called just before Madara calls the view. It should return either None or an response object. If it returns None, Madara will continue processing this request, executing any other `process_view()` middleware and, then, the appropriate view. If it returns an response object, Madara won’t bother calling the appropriate view; it’ll apply response middleware to that response and return the result.

Madara calls `process_exception()` when a view raises an exception. process_exception() should return either None or an response object.

### Configuration

The default configuration is as follows.

```
{
    "debug": False,
    "middlewares": [],
    "server_name": None,
    "host_matching": False,
    "subdomain_matching": False,
    "logger_handler": None,
}
```

- `debug` enable madara log some internal info.
- `middlewares` list config the app middleware chain.