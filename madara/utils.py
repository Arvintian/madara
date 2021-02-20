from werkzeug.wrappers import Response
from json import dumps
from importlib import import_module


text_type = str


def jsonify(*args, **kwargs):
    indent = None
    separators = (",", ":")

    if args and kwargs:
        raise TypeError("jsonify() behavior undefined when passed both args and kwargs")
    elif len(args) == 1:  # single args are passed directly to dumps()
        data = args[0]
    else:
        data = args or kwargs

    return Response(
        dumps(data, indent=indent, separators=separators) + "\n",
        mimetype="application/json",
    )


def reraise(tp, value, tb=None):
    if value.__traceback__ is not tb:
        raise value.with_traceback(tb)
    raise value


def _endpoint_from_view_func(view_func):
    """Internal helper that returns the default endpoint for a given
    function.  This always is the function name.
    """
    assert view_func is not None, "expected view func if endpoint is not provided."
    return view_func.__name__


def import_string(dotted_path):
    """
    Import a dotted module path and return the attribute/class designated by the
    last name in the path. Raise ImportError if the import failed.
    """
    try:
        module_path, class_name = dotted_path.rsplit('.', 1)
    except ValueError as err:
        raise ImportError("%s doesn't look like a module path" % dotted_path) from err

    module = import_module(module_path)

    try:
        return getattr(module, class_name)
    except AttributeError as err:
        raise ImportError('Module "%s" does not define a "%s" attribute/class' % (module_path, class_name)) from err


def load_config(kwargs: dict)->dict:
    config = {}
    for k, v in kwargs.get("config", {}).items():
        if isinstance(k, str):
            config.update({
                k: v,
                k.lower(): v,
            })
        else:
            config.update({k: v})
    return config
