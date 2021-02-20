from madara.utils import _endpoint_from_view_func


class BlueprintSetupState(object):

    def __init__(self, blueprint, app, options):
        self.app = app

        self.blueprint = blueprint

        self.options = options

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

        if endpoint is None:
            endpoint = _endpoint_from_view_func(view_func)

        self.app.add_url_rule(
            pattern,
            "%s.%s" % (self.blueprint.name, endpoint),
            view_func,
            **options
        )


class Blueprint(object):

    def __init__(self, name, url_prefix=None):
        self.name = name
        self.url_prefix = url_prefix
        self.deferred_functions = []

    def record(self, func):
        """Registers a function that is called when the blueprint is
        registered on the application.
        """
        self.deferred_functions.append(func)

    def make_setup_state(self, app, options):
        return BlueprintSetupState(self, app, options)

    def register(self, app, options):
        state = self.make_setup_state(app, options)
        for deferred in self.deferred_functions:
            deferred(state)

    def route(self, pattern, **options):

        def decorator(func):
            endpoint = options.pop("endpoint", func.__name__)
            self.add_url_rule(pattern, endpoint, func, **options)
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
