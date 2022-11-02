from werkzeug.routing import Map, Rule, MapAdapter
from werkzeug.exceptions import HTTPException, InternalServerError, NotFound
from werkzeug.datastructures import ImmutableDict
from werkzeug.serving import run_simple
from madara.blueprints import Blueprint
from madara.wrappers import Request, make_response
from madara.utils import _endpoint_from_view_func, import_string, load_config
from madara.compat import string_types
from madara.log import enable_pretty_logging
import logging
import traceback


class Madara(object):

    default_config = ImmutableDict(
        {
            "debug": False,
            "server_name": None,
            "middlewares": [],
            "host_matching": False,
            "subdomain_matching": False,
            "logger_handler": None,
        }
    )

    def __init__(self, config=None):
        self.config = dict(self.default_config)
        if not config is None:
            self.config.update(load_config(config))

        if self.config["debug"]:
            self.logger = enable_pretty_logging(logger=logging.getLogger("madara"), handler=self.config["logger_handler"], level=logging.DEBUG)
        else:
            self.logger = enable_pretty_logging(logger=logging.getLogger("madara"), handler=self.config["logger_handler"], level=logging.INFO)
        self.logger.propagate = False

        self.url_map: Map = Map()
        self.url_map.host_matching = self.config["host_matching"]
        self.subdomain_matching = self.config["subdomain_matching"]
        self.url_rule_class = Rule
        self.endpoint_map: dict = {}
        self.blueprints: dict = {}
        self._middleware_chain = None
        self._view_middleware = []
        self._exception_middleware = []
        self.load_middleware()

        if self.config["debug"]:
            self.logger.debug("madara config {}".format(self.config))

    def load_middleware(self):
        middlewares = self.config.get("middlewares", [])
        handler = self.dispatch_request
        for md in reversed(middlewares):
            mw = md
            if isinstance(md, str):
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
        if not self.subdomain_matching:
            subdomain = self.url_map.default_subdomain or None
        else:
            subdomain = None
        adapter: MapAdapter = self.url_map.bind_to_environ(request.environ, server_name=self.config["server_name"], subdomain=subdomain)
        try:
            endpoint, view_kwargs = adapter.match()
            endpoint_func = self.endpoint_map.get(endpoint, None)
            if not endpoint_func:
                raise NotFound()
            request.endpoint, request.view_args = endpoint, view_kwargs
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
            except Exception as re:
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
        return make_response(request, rv)

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        try:
            response = self._middleware_chain(request)
            return response(environ, start_response)
        except Exception as e:
            # process middleware chain __call__ error
            response = self.make_response(request, InternalServerError(original_exception=e))
            if not self._exception_middleware:
                self.logger.error(traceback.format_exc())
            else:
                # process exception by middleware
                try:
                    rv = self.process_exception_by_middleware(request, e)
                    if not rv is None:
                        response = self.make_response(request, rv)
                except Exception as re:
                    response = self.make_response(request, InternalServerError(original_exception=e))
            return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

    def run(self, host="0.0.0.0", port=5000):
        is_debug = True if self.config.get("debug", False) else False
        run_simple(host, port, self, use_debugger=is_debug, use_reloader=False)
