from werkzeug.wrappers import Request as __request_base
from werkzeug.wrappers import Response as __response_base
from werkzeug.datastructures import Headers
from madara.compat import text_type
from madara.utils import reraise, jsonify
import typing as t
import sys


class Request(__request_base):

    view_args: t.Optional[t.Dict[str, t.Any]] = None
    endpoint: t.Optional[str] = None


class Response(__response_base):
    pass


def make_response(request, *rv) -> Response:

    if not rv:
        return Response()

    if len(rv) == 1:
        rv = rv[0]

    status = headers = None

    # unpack tuple returns
    if isinstance(rv, tuple):
        len_rv = len(rv)

        # a 3-tuple is unpacked directly
        if len_rv == 3:
            rv, status, headers = rv
        # decide if a 2-tuple has status or headers
        elif len_rv == 2:
            if isinstance(rv[1], (Headers, dict, tuple, list)):
                rv, headers = rv
            else:
                rv, status = rv
        # other sized tuples are not allowed
        else:
            raise TypeError(
                "The view function did not return a valid response tuple."
                " The tuple must have the form (body, status, headers),"
                " (body, status), or (body, headers)."
            )

    # the body must not be None
    if rv is None:
        raise TypeError(
            "The view function did not return a valid response. The"
            " function either returned None or ended without a return"
            " statement."
        )

    # make sure the body is an instance of the response class
    if not isinstance(rv, Response):
        if isinstance(rv, (text_type, bytes, bytearray)):
            # let the response class set the status and headers instead of
            # waiting to do it manually, so that the class can handle any
            # special logic
            rv = Response(rv, status=status, headers=headers)
            status = headers = None
        elif isinstance(rv, dict):
            rv = jsonify(rv)
        elif isinstance(rv, Response) or callable(rv):
            # evaluate a WSGI callable, or coerce a different response
            # class to the correct type
            try:
                rv = Response.force_type(rv, request.environ)
            except TypeError as e:
                new_error = TypeError(
                    "{e}\nThe view function did not return a valid"
                    " response. The return type must be a string, dict, tuple,"
                    " Response instance, or WSGI callable, but it was a"
                    " {rv.__class__.__name__}.".format(e=e, rv=rv)
                )
                reraise(TypeError, new_error, sys.exc_info()[2])
        else:
            raise TypeError(
                "The view function did not return a valid"
                " response. The return type must be a string, dict, tuple,"
                " Response instance, or WSGI callable, but it was a"
                " {rv.__class__.__name__}.".format(rv=rv)
            )

    # prefer the status if it was provided
    if status is not None:
        if isinstance(status, (text_type, bytes, bytearray)):
            rv.status = status
        else:
            rv.status_code = status

    # extend existing headers with provided headers
    if headers:
        rv.headers.extend(headers)

    return rv
