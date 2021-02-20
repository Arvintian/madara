from werkzeug.wrappers import Request as RequestBase
from werkzeug.wrappers import Response as ResponseBase
from werkzeug.wrappers.json import JSONMixin as _JSONMixin


class Request(RequestBase, _JSONMixin):
    pass


class Response(ResponseBase):
    pass
