from madara.utils import _endpoint_from_view_func, import_string
from werkzeug.exceptions import HTTPException, NotFound


class BlueprintSetupState(object):

    def __init__(self, blueprint, app, options):
        self.app = app

        self.blueprint = blueprint

        self.options = options

        subdomain = self.options.get("subdomain")
        if subdomain is None:
            subdomain = self.blueprint.subdomain
        self.subdomain = subdomain

        url_prefix = self.options.get("url_prefix")
        if url_prefix is None:
            url_prefix = self.blueprint.url_prefix
        self.url_prefix = url_prefix

    def add_url_rule(self, pattern, endpoint=None, view_func=None, **options):
        if self.url_prefix is not None:
            if pattern:
                pattern = "/".join((self.url_prefix.rstrip("/"), pattern.lstrip("/")))
            else:
                pattern = self.url_prefix

        options.setdefault("subdomain", self.subdomain)

        if endpoint is None:
            endpoint = _endpoint_from_view_func(view_func)

        self.app.add_url_rule(
            pattern,
            "%s.%s" % (self.blueprint.name, endpoint),
            view_func,
            **options
        )


class Blueprint(object):

    def __init__(self, name, url_prefix=None, subdomain=None):
        self.name = name
        self.url_prefix = url_prefix
        self.subdomain = subdomain
        self.deferred_functions = []
        self._middleware_chain = None
        self._view_middleware = []
        self._exception_middleware = []
        self.endpoint_map = {}
        self.app = None

    def record(self, func):
        """
        Registers a function that is called when the blueprint is registered on the application.
        """
        self.deferred_functions.append(func)

    def make_setup_state(self, app, options):
        return BlueprintSetupState(self, app, options)

    def register(self, app, options: dict):
        self.app = app
        # register route rule
        state = self.make_setup_state(app, options)
        for deferred in self.deferred_functions:
            deferred(state)
        # load middlewares
        middlewares = options.get("middlewares", [])
        handler = self.dispatch_view
        for md in reversed(middlewares):
            mw = md
            if isinstance(md, str):
                mw = import_string(md)
            mw_instance = mw(handler, app)
            if hasattr(mw_instance, 'process_view'):
                self._view_middleware.insert(0, mw_instance.process_view)

            if hasattr(mw_instance, 'process_exception'):
                self._exception_middleware.append(mw_instance.process_exception)
            handler = mw_instance
        self._middleware_chain = handler

    def view_entry(self, request, **view_args):
        originl_exception = None
        rv = None
        try:
            rv = self._middleware_chain(request)
        except Exception as e:
            if self._exception_middleware:
                try:
                    rv = self.process_exception_by_middleware(request, e)
                except Exception as e:
                    originl_exception = e
            else:
                originl_exception = e

        if originl_exception:
            raise originl_exception
        return rv

    def dispatch_view(self, request):
        originl_exception = None
        rv = None
        try:
            endpoint, view_kwargs = request.endpoint, request.view_args
            endpoint_func = self.endpoint_map.get(endpoint, None)
            if not endpoint_func:
                raise NotFound()
            rv = self.process_view_by_middleware(request, endpoint_func, view_kwargs)
            if rv is None:
                rv = endpoint_func(request, **view_kwargs)
        except HTTPException as e:
            rv = e
        except Exception as e:
            if self._exception_middleware:
                try:
                    rv = self.process_exception_by_middleware(request, e)
                except Exception as e:
                    originl_exception = e
            else:
                originl_exception = e

        if originl_exception:
            raise originl_exception
        return rv

    def process_view_by_middleware(self, request, callback, callback_kwargs):
        """
        Pass the request and view_func、view_kwargs to the view middleware.
        Middleware process_view should return either None or a response.
        If it returns None, will continue processing this request, executing any other process_view() middleware and, then, the blueprint view_func.
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

    def route(self, pattern, **options):

        def decorator(func):
            endpoint = options.pop("endpoint", func.__name__)
            self.endpoint_map["%s.%s" % (self.name, endpoint)] = func
            self.add_url_rule(pattern, endpoint, self.view_entry, **options)
            return func

        return decorator

    def add_url_rule(self, pattern, endpoint=None, view_func=None, **options):

        if endpoint:
            assert "." not in endpoint, "Blueprint endpoints should not contain dots"
        if view_func and hasattr(view_func, "__name__"):
            assert (
                "." not in view_func.__name__
            ), "Blueprint view function name should not contain dots"
        self.record(lambda s: s.add_url_rule(pattern, endpoint, view_func, **options))
