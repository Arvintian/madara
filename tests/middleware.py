from madara.log import enable_pretty_logging
import logging
import traceback

logger = enable_pretty_logging(logger=logging.getLogger(__name__), level=logging.DEBUG)


class M1(object):

    def __init__(self, get_response, app):
        self.current_app = app
        self.get_response = get_response
        # One-time configuration and initialization.
        logger.info("m1 init")

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        logger.info("m1 process request")

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        logger.info("m1 process response")

        return response

    def process_view(self, request, callback, callback_kwargs):
        logger.info("m1 process view")
        return None

    def process_exception(self, request, exception):
        logger.info("m1 process exception: {}".format(exception))
        logger.error(traceback.format_exc())
        return None


class M2(object):

    def __init__(self, get_response, app):
        self.current_app = app
        self.get_response = get_response
        # One-time configuration and initialization.
        logger.info("m2 init")

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        logger.info("m2 process request")

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        logger.info("m2 process response")

        return response

    def process_view(self, request, callback, callback_kwargs):
        logger.info("m2 process view")
        return None

    def process_exception(self, request, exception):
        logger.info("m2 process exception")
        logger.error(traceback.format_exc())
        return {
            "code": -1
        }
