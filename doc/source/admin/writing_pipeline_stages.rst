========================================
Writing stages for the storage pipelines
========================================

Introduction
~~~~~~~~~~~~

A pipeline is a set of stages needed to process a request. When a new request
comes to Zaqar, first the message goes through the transport layer pipeline and
then through one of the storage layer pipelines depending on the type of
operation of each particular request. For example, if Zaqar receives a
request to make a queue-related operation, the storage layer pipeline will be
``queue pipeline``. Zaqar always has the actual storage controller as the
final storage layer pipeline stage.

By setting the options in the ``[storage]`` section of ``zaqar.conf``
you can add additional stages to these storage layer pipelines:

* **Claim pipeline**
* **Message pipeline** with built-in stage available to use:

   * ``zaqar.notification.notifier`` - sends notifications to the queue
     subscribers on each incoming message to the queue, i.e. enables
     notifications functionality.
* **Queue pipeline**
* **Subscription pipeline**

The storage layer pipelines options are empty by default, because additional
stages can affect the performance of Zaqar. Depending on the stages, the
sequence in which the option values are listed does matter or not.

You can add your own external stages to the storage layer pipelines.

Things to know before writing the stage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Stages in the pipeline must implement storage controller methods they need
to hook. You can find all available to hook methods in the abstract classes in
``zaqar/storage/base.py``. For example, if you're looking for all methods
available to hook for the queue storage layer pipeline, see ``Queue``
class in ``zaqar/storage/base.py``. As you can see, Zaqar's built-in stage
``zaqar.notification.notifier`` implements ``post`` method of
``zaqar.storage.base.Message`` abstract class.

A stage can halt the pipeline immediate by returning a value that is not
None; otherwise, processing will continue to the next stage, ending with the
actual storage controller.

.. warning::

   For the most of the cases it does not matter what non-None value the storage
   pipeline returns, but sometimes the returned value is used by the transport
   layer and you have to be careful. For example, during queue creation
   request, if the storage driver returns ``True``, the transport layer
   responds to the client with the ``201`` http response code, if ``False``,
   it responds with ``204`` http response code. See:
   ``zaqar.transport.wsgi.v2_0.queues.ItemResource#on_put``.

Zaqar finds stages with their source codes through the Python entry points
mechanism. All Python packages containing stages for Zaqar must register
their stages under ``zaqar.storage.stages`` entry point group during their
install either by ``setup.py`` or by ``setup.cfg``. If the stage is registered,
and the name of the stage's entry point is specified by the user in the one of
``zaqar.conf`` storage layer pipeline options, the stage will be loaded to
the particular storage layer pipeline. Zaqar imports stages as plugins. See
``zaqar.storage.pipeline#_get_storage_pipeline``.

For additional information about plugins see: `Stevedore - Creating Plugins`_
and `Stevedore - Loading the Plugins`_.

Example of external stage (written outside Zaqar package)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is an example of small package with a stage that can process queue-related
requests in Zaqar. The stage does not do anything useful, but is good as
example.

File tree structure of the package::

   .
   ├── setup.py
   └── ubershystages
       ├── __init__.py
       └── queues
           ├── __init__.py
           └── lovely.py

   2 directories, 4 files

``setup.py``:

.. code-block:: python

   from setuptools import setup, find_packages

   setup(
       name='ubershystages',
       version='1.0',

       description='Demonstration package for Zaqar with plugin pipeline stage',

       author='Ubershy',
       author_email='ubershy@gmail.com',

       url='',

       classifiers=['Development Status :: 3 - Alpha',
                    'License :: OSI Approved :: Apache Software License',
                    'Programming Language :: Python',
                    'Programming Language :: Python :: 2',
                    'Programming Language :: Python :: 2.7',
                    'Programming Language :: Python :: 3',
                    'Programming Language :: Python :: 3.5',
                    'Intended Audience :: Developers',
                    'Environment :: Console',
                    ],

       platforms=['Any'],

       scripts=[],

       packages=find_packages(),
       include_package_data=True,

       entry_points={
           'zaqar.storage.stages': [
               'ubershy.lovelyplugin = ubershystages.queues.lovely:LovelyStage',
           ],
       },

       zip_safe=False,
   )

``lovely.py``:

.. code-block:: python

   class LovelyStage(object):
       """This stage:
       1. Prints 'Lovely stage is processing request...' on each queue creation or
          deletion request.
       2. Prints 'Oh, what a lovely day!' on each creation request of a queue
          named 'lovely'.
       3. Prevents deletion of a queue named 'lovely' and prints 'Secretly keeping
          lovely queue' on such attempt.
       """

       def __init__(self, *args, **kwargs):
           print("Lovely stage is loaded!")

       def create(self, name, metadata=None, project=None):
           """Stage's method which processes queue creation request.

           :param name: The queue name
           :param project: Project id
           """

           self.printprocessing()
           if name == 'lovely':
               print("Oh, what a lovely day!")

       def delete(self, name, project=None):
           """Stage's method which processes queue deletion request.

           :param name: The queue name
           :param project: Project id
           :returns: Something non-None, if the queue has a name 'lovely'. It will
           stop further processing through the other stages of the pipeline, and
           the request will not reach the storage controller driver, preventing
           queue deletion from the database.
           """

           self.printprocessing()
           if name == 'lovely':
               print('Secretly keeping lovely queue')
               something = "shhh... it's a bad practice"
               return something

       def printprocessing(self):
           print('Lovely stage is processing request...')

To install the package to the system in the root directory of the package run:

.. code-block:: console

   # pip install -e .

In ``zaqar.conf`` add ``ubershy.lovelyplugin`` to the ``queue_pipeline``
option:

.. code-block:: ini

   [storage]
   queue_pipeline = ubershy.lovelyplugin

Start Zaqar:

.. code-block:: console

   $ zaqar-server

If the stage has successfully loaded to Zaqar you will see amongst terminal
output lines the ``Lovely stage is loaded!`` line. Then you can try to perform
queue create and queue delete operations with the queue 'lovely' and see what
will happen in Zaqar's database.

.. note::

  You can hold multiple stages in one package, just be sure that all stages
  will be registered as entry points. For example, in the ``setup.py`` you
  can register additional ``ubershy.nastyplugin`` stage:

  .. code-block:: python

     entry_points={
         'zaqar.storage.stages': [
             'ubershy.lovelyplugin = ubershystages.queues.lovely:LovelyStage',
             'ubershy.nastyplugin = ubershystages.messages.nasty:NastyStage',
         ],
     },

.. _`Stevedore - Creating Plugins`: https://docs.openstack.org/stevedore/latest/user/tutorial/creating_plugins.html
.. _`Stevedore - Loading the Plugins`: https://docs.openstack.org/stevedore/latest/user/tutorial/loading.html
