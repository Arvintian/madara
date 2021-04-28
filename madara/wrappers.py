from werkzeug.wrappers import Request as RequestBase
from werkzeug.wrappers import Response as ResponseBase
from werkzeug.wrappers.json import JSONMixin as _JSONMixin
import typing as t


class Request(RequestBase, _JSONMixin):

    view_args: t.Optional[t.Dict[str, t.Any]] = None


class Response(ResponseBase):
    pass
