..
      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

========================
Welcome new contributors
========================

First Steps
===========

It's very great that you're interested in contributing to Zaqar.

First of all, make sure you join Zaqar communication forums:

* Subscribe to Zaqar `mailing lists`_.
* Join Zaqar team on IRC. You can chat with us directly in the
  ``#openstack-zaqar`` channel on ``OFTC``. If you don't know
  how to use IRC, you can find some directions in `OpenStack IRC wiki`_.
* Answer and ask questions on `Ask OpenStack`_.

How can I contribute?
=====================

There are many ways you can contribute to Zaqar. Of course coding is one, but
you can also join Zaqar as a tester, documenter, designer or translator.

Coding
------

Bug fixing
^^^^^^^^^^

The first area where you can help is bug fixing. ``Confirmed`` bugs are usually
your best choice. ``Triaged`` bugs should even contain tips on how they
should be fixed. You can find both of them in
`Zaqar's Confirmed and Triaged bugs`_ web page.

Once you selected the bug you want to work on, go ahead and assign it to
yourself, branch the code, implement the fix, and propose your change for
review. You can find information on how to do it in
:doc:`first_patch` manual.

Some easy-to-fix bugs may be marked with the ``low-hanging-fruit`` tag: those
are good targets for a beginner.

Bug triaging
^^^^^^^^^^^^

You can also help Zaqar with bug triaging. Reported bugs need care:
prioritizing them correctly, confirming them, making sure they don't go stale.
All those tasks help immensely. If you want to start contributing in coding,
but you are not a hardcore developer, consider helping in this area.

Bugs can be marked with different tags according to their status:

* ``New`` bugs are those bugs that have been reported by a user but haven't
  been verified by the community yet.
* ``Confirmed`` bugs are those bugs that have been reproduced by someone else
  than the reporter.
* ``Triaged`` bugs are those bugs that have been reproduced by a core
  developer.
* ``Incomplete`` bugs are those bugs that don't have enough information to be
  reproduced.
* ``In Progress`` bugs are those bugs that are being fixed by some developer.
  This status is set automatically by the Gerrit review system once a fix is
  proposed by a developer. You don't need to set it manually.
* ``Invalid`` bugs are those bugs that don't qualify as a bug. Usually a
  support request or something unrelated to the project.

You can learn more about this in Launchpad's `Of Bugs and Statuses`_.

You only have to worry about ``New`` bugs. If you can reproduce them, you can
mark them as ``Confirmed``. If you cannot reproduce them, you can ask the
reported to provide more information and mark them as ``Incomplete``. If you
consider that they aren't bugs, mark them as ``Invalid`` (Be careful with this.
Asking someone else in Zaqar is always a good idea).

Also, you can contribute instructions on how to fix a given bug.

Check out the `Bug Triage`_ wiki for more information.

Reviewing
^^^^^^^^^

Every patch submitted to OpenStack gets reviewed before it can be approved and
merged. Zaqar gets a lot of contributions and everyone can (and is encouraged
to) review Zaqar's existing patches. Pick an open review and go through
it, test it if possible, and leave a comment with a ``+1`` or ``-1`` vote
describing what you discovered. If you're planning on submitting patches of
your own, it's a great way to learn about what the community cares about and to
learn about the code base.

Make sure you read :doc:`first_review` manual.

Feature development
^^^^^^^^^^^^^^^^^^^

Once you get familiar with the code, you can start to contribute new features.
New features get implemented every 6 months in `OpenStack development cycle`_.
We use `Launchpad Blueprints`_ to track the design and implementation of
significant features, and Zaqar team uses Design Summits every 6 months to
get together and discuss things in person with the rest of the community. Code
should be proposed for inclusion before Zaqar reach the final feature milestone
of the development cycle.

Testing
-------

Testing efforts are highly related to coding. If you find that there are test
cases missing or that some tests could be improved, you are encouraged to
report it as a bug and then provide your fix.

See :doc:`running_tests` and :doc:`test_suite` for information on how to run
tests and how the tests are organized in Zaqar.

See :doc:`first_patch` for information on how to provide your fix.


Documenting
-----------

You can contribute to `Zaqar's Contributor Documentation`_ which you are
currently reading and to `Zaqar's Wiki`_.

To fix a documentation bug check the bugs marked with the ``doc`` tag in
Zaqar's bug list. In case that you want to report a documentation bug, then
don't forget to add the ``doc`` tag to it.

`Zaqar's Contributor Documentation`_ is compiled from source files in ``.rst``
(reStructuredText) format located in ``doc/source/`` directory in Zaqar
repository. The `"openstack-manuals" project`_ houses the documentation that is
published to ``docs.openstack.org``.

Before contributing to `Zaqar's Contributor Documentation`_ you have to read
:doc:`first_patch` manual and `OpenStack Documentation Contributor Guide`_.

Also, you can monitor `Ask OpenStack`_ to curate the best answers that can be
folded into the documentation.

Designing
---------

Zaqar doesn't have a user interface yet. Zaqar team is working to
`integrate Zaqar to the OpenStack Dashboard (Horizon)`_.

If you're a designer or usability professional your help will be really
appreciated. Whether it's reviewing upcoming features as a user and giving
feedback, designing features, testing designs or features with users, or
helping to build use cases and requirements, everything is useful.

Translating
-----------

You can translate Zaqar to language you know.
Read the `Translation wiki page`_ for more information on how OpenStack manages
translations. Zaqar has adopted Zanata, and you can use the
`OpenStack Zanata site`_ as a starting point to translate any of the OpenStack
projects, including Zaqar. It's easier to start translating directly on the
`OpenStack Zanata site`_, as there is no need to download any files or
applications to get started.


.. _`mailing lists` : https://wiki.openstack.org/wiki/MailingLists
.. _`OpenStack IRC wiki` : https://wiki.openstack.org/wiki/IRC
.. _`Ask OpenStack` : https://ask.openstack.org/
.. _`Zaqar's Confirmed and Triaged bugs` : https://bugs.launchpad.net/zaqar/+bugs?field.searchtext=&orderby=-importance&search=Search&field.status%3Alist=CONFIRMED&field.status%3Alist=TRIAGED&assignee_option=any&field.assignee=&field.bug_reporter=&field.bug_commenter=&field.subscriber=&field.structural_subscriber=&field.tag=&field.tags_combinator=ANY&field.has_cve.used=&field.omit_dupes.used=&field.omit_dupes=on&field.affects_me.used=&field.has_patch.used=&field.has_branches.used=&field.has_branches=on&field.has_no_branches.used=&field.has_no_branches=on&field.has_blueprints.used=&field.has_blueprints=on&field.has_no_blueprints.used=&field.has_no_blueprints=on
.. _`Of Bugs and Statuses` : http://blog.launchpad.net/general/of-bugs-and-statuses
.. _`Bug Triage` : https://wiki.openstack.org/wiki/BugTriage
.. _`OpenStack development cycle` : https://wiki.openstack.org/wiki/ReleaseCycle
.. _`Launchpad Blueprints` : https://wiki.openstack.org/wiki/Blueprints
.. _`OpenStack Documentation Contributor Guide` : https://docs.openstack.org/contributor-guide/index.html
.. _`Zaqar's Contributor Documentation` : https://docs.openstack.org/zaqar/latest/
.. _`Zaqar's Wiki` : https://wiki.openstack.org/wiki/Zaqar
.. _`"openstack-manuals" project` : https://wiki.openstack.org/wiki/Documentation
.. _`integrate Zaqar to the OpenStack Dashboard (Horizon)` : https://blueprints.launchpad.net/zaqar-ui/
.. _`Translation wiki page` : https://wiki.openstack.org/wiki/Translations#Translation_.26_Management
.. _`OpenStack Zanata site` : https://translate.openstack.org/
