from werkzeug.wrappers import BaseResponse
from werkzeug.routing import Map, Rule, MapAdapter
from werkzeug.exceptions import HTTPException, InternalServerError, NotFound
from werkzeug.datastructures import Headers
from werkzeug.serving import run_simple
from madara.blueprints import Blueprint
from madara.wrappers import Request, Response
from madara.utils import jsonify, reraise, _endpoint_from_view_func, import_string, load_config
from madara.compat import text_type, string_types
from madara.log import enable_pretty_logging
import sys
import logging
import traceback


class Madara(object):

    def __init__(self, **kwargs):
        self.config = load_config(kwargs)
        self.bootstrap()
        self.url_map: Map = Map()
        self.url_rule_class = Rule
        self.endpoint_map: dict = {}
        self.blueprints: dict = {}
        self.response_class = Response
        self._middleware_chain = None
        self._view_middleware = []
        self._exception_middleware = []
        self.load_middleware()

    def bootstrap(self):
        if self.config.get("debug"):
            self.logger = enable_pretty_logging(logger=logging.getLogger("madara"), level=logging.DEBUG)
        else:
            self.logger = enable_pretty_logging(logger=logging.getLogger("madara"), level=logging.WARNING)

    def load_middleware(self):
        middlewares = self.config.get("middlewares", [])
        handler = self.dispatch_request
        for md in reversed(middlewares):
            mw = import_string(md)
            mw_instance = mw(handler, self)
            if hasattr(mw_instance, 'process_view'):
                self._view_middleware.insert(0, mw_instance.process_view)

            if hasattr(mw_instance, 'process_exception'):
                self._exception_middleware.append(mw_instance.process_exception)
            handler = mw_instance

        self._middleware_chain = handler

    def add_url_rule(self, pattern: str, endpoint=None, view_func=None, provide_automatic_options=None, **options):
        if endpoint is None:
            endpoint = _endpoint_from_view_func(view_func)
        options["endpoint"] = endpoint
        methods = options.pop("methods", None)

        # if the methods are not given and the view_func object knows its
        # methods we can use that instead.  If neither exists, we go with
        # a tuple of only ``GET`` as default.
        if methods is None:
            methods = getattr(view_func, "methods", None) or ("GET",)
        if isinstance(methods, string_types):
            raise TypeError(
                "Allowed methods have to be iterables of strings, "
                'for example: @app.route(..., methods=["POST"])'
            )
        methods = set(item.upper() for item in methods)

        # Methods that should always be added
        required_methods = set(getattr(view_func, "required_methods", ()))

        if provide_automatic_options is None:
            provide_automatic_options = getattr(
                view_func, "provide_automatic_options", None
            )

        if provide_automatic_options is None:
            if "OPTIONS" not in methods:
                provide_automatic_options = True
                required_methods.add("OPTIONS")
            else:
                provide_automatic_options = False

        # Add the required methods now.
        methods |= required_methods

        rule = self.url_rule_class(pattern, methods=methods, **options)
        rule.provide_automatic_options = provide_automatic_options

        self.url_map.add(rule)
        if view_func is not None:
            old_func = self.endpoint_map.get(endpoint)
            if old_func is not None and old_func != view_func:
                raise AssertionError(
                    "View function mapping is overwriting an "
                    "existing endpoint function: %s" % endpoint
                )
            self.endpoint_map[endpoint] = view_func

    def route(self, pattern: str, **options):
        def decorator(func):
            endpoint = options.pop("endpoint", None)
            self.add_url_rule(pattern, endpoint, func, **options)
            return func

        return decorator

    def register_blueprint(self, blueprint: Blueprint, **options):

        if blueprint.name in self.blueprints:
            assert self.blueprints[blueprint.name] is blueprint, (
                "A name collision occurred between blueprints %r and %r. Both"
                ' share the same name "%s". Blueprints that are created on the'
                " fly need unique names."
                % (blueprint, self.blueprints[blueprint.name], blueprint.name)
            )
        else:
            self.blueprints[blueprint.name] = blueprint
        blueprint.register(self, options)

    def dispatch_request(self, request):
        adapter: MapAdapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, view_kwargs = adapter.match()
            endpoint_func = self.endpoint_map.get(endpoint, None)
            if not endpoint_func:
                raise NotFound()
            rv = self.process_view_by_middleware(request, endpoint_func, view_kwargs)
            if rv is None:
                rv = endpoint_func(request, **view_kwargs)
            return self.make_response(request, rv)
        except HTTPException as e:
            return e
        except Exception as e:
            if not self._exception_middleware:
                # if no exception process middleware log the traceback.
                self.logger.error(traceback.format_exc())
            try:
                rv = self.process_exception_by_middleware(request, e)
                if rv is None:
                    return InternalServerError(original_exception=e)
                return self.make_response(request, rv)
            except Exception as e:
                # if exception process middleware raise a exception, log the traceback and return an InternalServerError.
                self.logger.error(traceback.format_exc())
                return InternalServerError(original_exception=e)

    def process_view_by_middleware(self, request, callback, callback_kwargs):
        """
        Pass the request and view_func、view_kwargs to the view middleware.
        Middleware process_view should return either None or a response.
        If it returns None, will continue processing this request, executing any other process_view() middleware and, then, the appropriate view_func.
        """
        for middleware_method in self._view_middleware:
            response = middleware_method(request, callback, callback_kwargs)
            if response:
                return response
        return None

    def process_exception_by_middleware(self, request, exception):
        """
        Pass the exception to the exception middleware. If no middleware
        return a response for this exception, return None.
        """
        for middleware_method in self._exception_middleware:
            response = middleware_method(request, exception)
            if response:
                return response
        return None

    def make_response(self, request, rv):

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
        if not isinstance(rv, self.response_class):
            if isinstance(rv, (text_type, bytes, bytearray)):
                # let the response class set the status and headers instead of
                # waiting to do it manually, so that the class can handle any
                # special logic
                rv = self.response_class(rv, status=status, headers=headers)
                status = headers = None
            elif isinstance(rv, dict):
                rv = jsonify(rv)
            elif isinstance(rv, BaseResponse) or callable(rv):
                # evaluate a WSGI callable, or coerce a different response
                # class to the correct type
                try:
                    rv = self.response_class.force_type(rv, request.environ)
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

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        response = self._middleware_chain(request)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

    def run(self, host="0.0.0.0", port=5000):
        is_debug = True if self.config.get("debug", False) else False
        run_simple(host, port, self, use_debugger=is_debug, use_reloader=False)
