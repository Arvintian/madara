from madara.app import Madara
from madara.wrappers import Request
from madara.blueprints import Blueprint

app = Madara(config={
    "debug": True,
    "middlewares": [
        "tests.middleware.M1",
        "tests.middleware.M2",
    ],
    # "server_name": "example.com",
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


#app.register_blueprint(bp_example, url_prefix="/blueprint", subdomain="public")
app.register_blueprint(bp_example, url_prefix="/blueprint")

if __name__ == "__main__":
    app.run()
