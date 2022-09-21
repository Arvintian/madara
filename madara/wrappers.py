from werkzeug.wrappers import Request as RequestBase
from werkzeug.wrappers import Response as ResponseBase
import typing as t


class Request(RequestBase):

    view_args: t.Optional[t.Dict[str, t.Any]] = None
    endpoint: t.Optional[str] = None


class Response(ResponseBase):
    pass
