import logging
from logging import StreamHandler
import sys

unicode_type = str
basestring_type = str
_TO_UNICODE_TYPES = (unicode_type, type(None))


def to_unicode(value):
    """Converts a string argument to a unicode string.
    If the argument is already a unicode string or None, it is returned
    unchanged.  Otherwise it must be a byte string and is decoded as utf8.
    """
    if isinstance(value, _TO_UNICODE_TYPES):
        return value
    if not isinstance(value, bytes):
        raise TypeError(
            "Expected bytes, unicode, or None; got %r" % type(value)
        )
    return value.decode("utf-8")


# to_unicode was previously named _unicode not because it was private,
# but to avoid conflicts with the built-in unicode() function/type
_unicode = to_unicode

try:
    import colorama
except ImportError:
    colorama = None

try:
    import curses
except ImportError:
    curses = None


def _stderr_supports_color():
    try:
        if hasattr(sys.stderr, 'isatty') and sys.stderr.isatty():
            if curses:
                curses.setupterm()
                if curses.tigetnum("colors") > 0:
                    return True
            elif colorama:
                if sys.stderr is getattr(colorama.initialise, 'wrapped_stderr',
                                         object()):
                    return True
    except Exception:
        # Very broad exception handling because it's always better to
        # fall back to non-colored logs than to break at startup.
        pass
    return False


def _safe_unicode(s):
    try:
        return _unicode(s)
    except UnicodeDecodeError:
        return repr(s)


class LogFormatter(logging.Formatter):
    """Log formatter used from Tornado.
    """
    DEFAULT_FORMAT = '%(color)s[%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d]%(end_color)s %(message)s'
    DEFAULT_DATE_FORMAT = '%y%m%d %H:%M:%S'
    DEFAULT_COLORS = {
        logging.DEBUG: 4,  # Blue
        logging.INFO: 2,  # Green
        logging.WARNING: 3,  # Yellow
        logging.ERROR: 1,  # Red
    }

    def __init__(self, fmt=DEFAULT_FORMAT, datefmt=DEFAULT_DATE_FORMAT, style='%', color=True, colors=DEFAULT_COLORS):
        """
        :arg bool color: Enables color support.
        :arg string fmt: Log message format.
          It will be applied to the attributes dict of log records. The
          text between ``%(color)s`` and ``%(end_color)s`` will be colored
          depending on the level if color support is on.
        :arg dict colors: color mappings from logging level to terminal color
          code
        :arg string datefmt: Datetime format.
          Used for formatting ``(asctime)`` placeholder in ``prefix_fmt``.
        """
        logging.Formatter.__init__(self, datefmt=datefmt)
        self._fmt = fmt

        self._colors = {}
        if color and _stderr_supports_color():
            if curses is not None:
                # The curses module has some str/bytes confusion in
                # python3.  Until version 3.2.3, most methods return
                # bytes, but only accept strings.  In addition, we want to
                # output these strings with the logging module, which
                # works with unicode strings.  The explicit calls to
                # unicode() below are harmless in python2 but will do the
                # right conversion in python 3.
                fg_color = (curses.tigetstr("setaf") or
                            curses.tigetstr("setf") or "")
                if (3, 0) < sys.version_info < (3, 2, 3):
                    fg_color = unicode_type(fg_color, "ascii")

                for levelno, code in colors.items():
                    self._colors[levelno] = unicode_type(curses.tparm(fg_color, code), "ascii")
                self._normal = unicode_type(curses.tigetstr("sgr0"), "ascii")
            else:
                # If curses is not present (currently we'll only get here for
                # colorama on windows), assume hard-coded ANSI color codes.
                for levelno, code in colors.items():
                    self._colors[levelno] = '\033[2;3%dm' % code
                self._normal = '\033[0m'
        else:
            self._normal = ''

    def format(self, record):
        try:
            message = record.getMessage()
            assert isinstance(message, basestring_type)  # guaranteed by logging
            # Encoding notes:  The logging module prefers to work with character
            # strings, but only enforces that log messages are instances of
            # basestring.  In python 2, non-ascii bytestrings will make
            # their way through the logging framework until they blow up with
            # an unhelpful decoding error (with this formatter it happens
            # when we attach the prefix, but there are other opportunities for
            # exceptions further along in the framework).
            #
            # If a byte string makes it this far, convert it to unicode to
            # ensure it will make it out to the logs.  Use repr() as a fallback
            # to ensure that all byte strings can be converted successfully,
            # but don't do it by default so we don't add extra quotes to ascii
            # bytestrings.  This is a bit of a hacky place to do this, but
            # it's worth it since the encoding errors that would otherwise
            # result are so useless (and tornado is fond of using utf8-encoded
            # byte strings wherever possible).
            record.message = _safe_unicode(message)
        except Exception as e:
            record.message = "Bad message (%r): %r" % (e, record.__dict__)

        record.asctime = self.formatTime(record, self.datefmt)

        if record.levelno in self._colors:
            record.color = self._colors[record.levelno]
            record.end_color = self._normal
        else:
            record.color = record.end_color = ''

        formatted = self._fmt % record.__dict__

        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            # exc_text contains multiple lines.  We need to _safe_unicode
            # each line separately so that non-utf8 bytes don't cause
            # all the newlines to turn into '\n'.
            lines = [formatted.rstrip()]
            lines.extend(_safe_unicode(ln) for ln in record.exc_text.split('\n'))
            formatted = '\n'.join(lines)
        return formatted.replace("\n", "\n    ")


def enable_pretty_logging(logger, handler=None, color=True, level=logging.WARNING):
    """Turns on formatted logging output as configured.
    """
    if not handler:
        channel = StreamHandler()
    else:
        channel = handler
    channel.setFormatter(LogFormatter(color=color))
    logger.addHandler(channel)
    logger.setLevel(level)
    return logger
