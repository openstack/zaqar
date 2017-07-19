========================
Zaqar style commandments
========================

- Step 1: Read the OpenStack Style Commandments
  https://docs.openstack.org/hacking/latest/
- Step 2: Read on for Zaqar specific commandments

General
-------
- Optimize for readability; whitespace is your friend.
- Use blank lines to group related logic.
- All classes must inherit from ``object`` (explicitly).
- Use single-quotes for strings unless the string contains a
  single-quote.
- Use the double-quote character for blockquotes (``"""``, not ``'''``)
- USE_ALL_CAPS_FOR_GLOBAL_CONSTANTS

Comments
--------
- In general use comments as "memory pegs" for those coming after you up
  the trail.
- Guide the reader though long functions with a comments introducing
  different sections of the code.
- Choose clean, descriptive names for functions and variables to make
  them self-documenting.
- Add ``# NOTE(termie): blah blah...`` comments to clarify your intent, or
  to explain a tricky algorithm, when it isn't obvious from just reading
  the code.


Identifiers
-----------
- Don't use single characters in identifiers except in trivial loop variables and mathematical algorithms.
- Avoid abbreviations, especially if they are ambiguous or their meaning would not be immediately clear to the casual reader or newcomer.

Wrapping
--------
Wrap long lines by using Python's implied line continuation inside
parentheses, brackets and braces. Make sure to indent the continued
line appropriately. The preferred place to break around a binary
operator is after the operator, not before it.

Example::

  class Rectangle(Blob):

      def __init__(self, width, height,
                   color='black', emphasis=None, highlight=0):

          # More indentation included to distinguish this from the rest.
          if (width == 0 and height == 0 and
                  color == 'red' and emphasis == 'strong' or
                  highlight > 100):
              raise ValueError('sorry, you lose')

          if width == 0 and height == 0 and (color == 'red' or
                                             emphasis is None):
              raise ValueError("I don't think so -- values are {0}, {1}".format(
                               width, height))

          msg = ('this is a very long string that goes on and on and on and'
                 'on and on and on...')

          super(Rectangle, self).__init__(width, height,
                                          color, emphasis, highlight)


Imports
-------
- Classes and functions may be hoisted into a package namespace, via __init__ files, with some discretion.

More Import Examples
--------------------

**INCORRECT** ::

  import zaqar.transport.wsgi as wsgi

**CORRECT** ::

  from zaqar.transport import wsgi

Docstrings
----------

Docstrings are required for all functions and methods.

Docstrings should ONLY use triple-double-quotes (``"""``)

Single-line docstrings should NEVER have extraneous whitespace
between enclosing triple-double-quotes.

**INCORRECT** ::

  """ There is some whitespace between the enclosing quotes :( """

**CORRECT** ::

  """There is no whitespace between the enclosing quotes :)"""

Docstrings should document default values for named arguments
if they're not None

Docstrings that span more than one line should look like this:

Example::

  """Single-line summary, right after the opening triple-double-quote.

  If you are going to describe parameters and return values, use Sphinx; the
  appropriate syntax is as follows.

  :param foo: the foo parameter
  :param bar: (Default True) the bar parameter
  :param foo_long_bar: the foo parameter description is very
    long so we have to split it in multiple lines in order to
    keep things ordered
  :returns: return_type -- description of the return value
  :returns: description of the return value
  :raises ValueError: if the message_body exceeds 160 characters
  :raises TypeError: if the message_body is not a basestring
  """

**DO NOT** leave an extra newline before the closing triple-double-quote.

Creating Unit Tests
-------------------
NOTE: 100% coverage is required

Logging
-------
Use __name__ as the name of your logger and name your module-level logger
objects 'LOG'::

    LOG = logging.getLogger(__name__)
