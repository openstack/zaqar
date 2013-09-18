Marconi Style Commandments
==========================

- Step 1: Read http://www.python.org/dev/peps/pep-0008/
- Step 2: Read http://www.python.org/dev/peps/pep-0008/ again
- Step 3: Read on


General
-------
- Optimize for readability; whitespace is your friend.
- Put two newlines between top-level code (funcs, classes, etc.)
- Put one newline between methods in classes and anywhere else.
- Use blank lines to group related logic.
- Never write ``except:`` (use ``except Exception:`` instead, at
  the very least).
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
- Include your name with TODOs as in ``# TODO(termie): blah blah...``.
- Add ``# NOTE(termie): blah blah...`` comments to clarify your intent, or
  to explain a tricky algorithm, when it isn't obvious from just reading
  the code.


Identifiers
-----------
- Do not give anything the same name as a built-in or reserved word.
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
- Only modules may be imported
- Do not make relative imports
- Order your imports by the full module path
- Classes and functions may be hoisted into a package namespace, via __init__ files, with some discretion.
- Organize your imports according to the template given below

Template::

  {{stdlib imports in human alphabetical order}}
  \n
  {{third-party lib imports in human alphabetical order}}
  \n
  {{marconi imports in human alphabetical order}}
  \n
  \n
  {{begin your code}}


Human Alphabetical Order Examples
---------------------------------
Example::

  import logging
  import time
  import unittest

  import eventlet

  import marconi.common
  from marconi import test
  import marconi.queues.transport


More Import Examples
--------------------

**INCORRECT** ::

  import marconi.queues.transport.wsgi as wsgi

**CORRECT** ::

  from marconi.queues.transport import wsgi

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
    keey things ordered
  :returns: return_type -- description of the return value
  :returns: description of the return value
  :raises: AttributeError, KeyError
  """

**DO NOT** leave an extra newline before the closing triple-double-quote.


Dictionaries/Lists
------------------
If a dictionary (dict) or list object is longer than 80 characters, its items
should be split with newlines. Embedded iterables should have their items
indented. Additionally, the last item in the dictionary should have a trailing
comma. This increases readability and simplifies future diffs.

Example::

  my_dictionary = {
      "image": {
          "name": "Just a Snapshot",
          "size": 2749573,
          "properties": {
               "user_id": 12,
               "arch": "x86_64",
          },
          "things": [
              "thing_one",
              "thing_two",
          ],
          "status": "ACTIVE",
      },
  }


Calling Methods
---------------
Calls to methods 80 characters or longer should format each argument with
newlines. This is not a requirement, but a guideline::

    unnecessarily_long_function_name('string one',
                                     'string two',
                                     kwarg1=constants.ACTIVE,
                                     kwarg2=['a', 'b', 'c'])


Rather than constructing parameters inline, it is better to break things up::

    list_of_strings = [
        'what_a_long_string',
        'not as long',
    ]

    dict_of_numbers = {
        'one': 1,
        'two': 2,
        'twenty four': 24,
    }

    object_one.call_a_method('string three',
                             'string four',
                             kwarg1=list_of_strings,
                             kwarg2=dict_of_numbers)


Internationalization (i18n) Strings
-----------------------------------
In order to support multiple languages, we have a mechanism to support
automatic translations of exception and log strings.

Example::

    msg = _("An error occurred")
    raise HTTPBadRequest(explanation=msg)

If you have a variable to place within the string, first internationalize the
template string then do the replacement.

Example::

    msg = _("Missing parameter: {0}").format("flavor",)
    LOG.error(msg)

If you have multiple variables to place in the string, use keyword parameters.
This helps our translators reorder parameters when needed.

Example::

    msg = _("The server with id {s_id} has no key {m_key}")
    LOG.error(msg.format(s_id=1234", m_key=imageId"))


Creating Unit Tests
-------------------
For every any change, unit tests should be created that both test and
(implicitly) document the usage of said feature. If submitting a patch for a
bug that had no unit test, a new passing unit test should be added. If a
submitted bug fix does have a unit test, be sure to add a new one that fails
without the patch and passes with the patch.

NOTE: 100% coverage is required

openstack-common
----------------

A number of modules from openstack-common are imported into the project.

These modules are "incubating" in openstack-common and are kept in sync
with the help of openstack-common's update.py script. See:

  http://wiki.openstack.org/CommonLibrary#Incubation

The copy of the code should never be directly modified here. Please
always update openstack-common first and then run the script to copy
the changes across.


Logging
-------
Use __name__ as the name of your logger and name your module-level logger
objects 'LOG'::

    LOG = logging.getLogger(__name__)
