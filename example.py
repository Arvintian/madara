from madara.app import Madara
from madara.wrappers import Request
from madara.blueprints import Blueprint
from tests.middleware import M2, M3

app = Madara(config={
    "debug": True,
    "middlewares": [
        "tests.middleware.M1",
        # "tests.middleware.M2",
        M2,
    ],
    # "server_name": "example.com",
})


bp_example = Blueprint("bp_example")


@app.route("/error", methods=["GET"])
def app_error(request: Request):
    raise Exception("test except")


@app.route("/item/<int:the_id>", methods=["GET"])
def app_route(request: Request, the_id):
    print(request.view_args)
    return "item id is {}".format(the_id)


@bp_example.route("/item/<int:the_id>", methods=["POST"])
def blueprint_route(request: Request, the_id):
    data = request.get_json()
    # raise Exception("ssssssss")
    return {
        "code": 0,
        "the_id": the_id,
        "result": data,
    }


#app.register_blueprint(bp_example, url_prefix="/blueprint", subdomain="public")
app.register_blueprint(bp_example, url_prefix="/blueprint", middlewares=[M3])

if __name__ == "__main__":
    app.run()
