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

================
Your first patch
================

This section describes how to create your first patch and upload it to
Gerrit_ for reviewing.


Create your contributor accounts and set up your code environment
-----------------------------------------------------------------

Accounts setup
##############

You will need to create a Launchpad_ account to login to the Gerrit_ review
system dashboard.
This is also useful for automatically crediting bug fixes to you when you
address them with your code commits. You will also have to sign the
`Contributors License Agreement`_ and `join the OpenStack Foundation`_.
It is a good idea to use the same email all of these accounts to
avoid hooks errors.

Visit the `Gerrit Workflow's account setup`_ section in the wiki to get
more information on setting up your accounts.

.. _Launchpad: https://launchpad.net/
.. _Gerrit: https://review.opendev.org/
.. _`Contributors License Agreement`: https://docs.openstack.org/infra/manual/developers.html#account-setup
.. _`join the OpenStack Foundation`: https://www.openstack.org/join/
.. _`Gerrit Workflow's account setup`: https://docs.openstack.org/infra/manual/developers.html#account-setup

SSH setup
#########

You are going to need to create and upload an SSH key to Gerrit to be able to
commit changes for review. To create an SSH key:

.. code-block:: console

   $ ssh-keygen –t rsa

You can optionally enter a password to enhance security.

View and copy your SSH key:

.. code-block:: console

   $ less ~/.ssh/id_rsa.pub

Now you can `upload the SSH key to Gerrit`_.

.. _`upload the SSH key to Gerrit`: https://review.opendev.org/#/settings/ssh-keys

Git Review installation
#######################

Before you start working, make sure you have ``git-review`` installed on your
system.

You can install it with the following command:

.. code-block:: console

   $ pip install git-review

``Git-review`` checks if you can authenticate to Gerrit with your SSH key.
It will ask you for your username. You can configure your Gerrit username so
you don't have to keep re-entering it every time you want to use
``git-review``:

.. code-block:: console

   $ git config --global gitreview.username yourgerritusername

You can also save some time by entering your email and your name:

.. code-block:: console

   $ git config --global gitreview.email "yourgerritemail"
   $ git config --global gitreview.name "Firstname Lastname"

You can view your Gerrit user name in the `settings page`_.

.. _`settings page`: https://review.opendev.org/#/settings/

Project setup
#############

Clone the Zaqar repository with the following git command:

.. code-block:: console

  $ git clone https://git.openstack.org/openstack/zaqar.git

For information on how to set up the Zaqar development environment
see :doc:`development.environment`.

Before writing code, you will have to do some configurations to connect your
local repository with Gerrit. You will only need to do this your first time
setting up the development environment.

You can set ``git-review`` to configure the project and install the Gerrit
change-id commit hook with the following command:

.. code-block:: console

   $ cd zaqar
   $ git review -s

If you get the error "We don't know where your Gerrit is", you will need to add
a new git remote. The URL should be in the error message. Copy that and create
the new remote. It looks something like:

.. code-block:: console

   $ git remote add gerrit ssh://<username>@review.opendev.org:29418/openstack/zaqar.git

In the project directory you have a hidden ``.git`` directory and a
``.gitreview`` file. You can view them with the following command:

.. code-block:: console

   $ ls -la

Making a patch
--------------

Pick or report a bug
####################

You can start tackling some bugs from the `bugs list in Launchpad`_.
If you find a bug you want to work on, assign yourself. Make sure to read the
bug report. If you need more information, ask the reporter to provide more
details through a comment on Launchpad or through IRC or email.

If you find a bug, look through Launchpad to see if it has been reported. If it
hasn't, report the bug, and ask for another developer to confirm it. You can
start working on it if another developer confirms the bug.

Here are some details you might want to include when filling out a bug report:

* The release, or milestone, or commit ID corresponding to the software that
  you are running
* The operating system and version where you've identified the bug
* Steps to reproduce the bug, including what went wrong
* Description of the expected results instead of what you saw
* Portions of your log files so that you include only relevant excerpts

In the bug comments, you can contribute instructions on how to fix a given bug,
and set the status to "Triaged".

You can read more about `Launchpad bugs`_ in the official guide.

.. _`bugs list in Launchpad`: https://bugs.launchpad.net/zaqar
.. _`Launchpad bugs`:  https://docs.openstack.org/project-team-guide/bugs.html

Workflow
########

Make sure your repo is up to date. You can update it with the following git
commands:

.. code-block:: console

    $ git remote update
    $ git checkout master
    $ git pull --ff-only origin master

Create a topic branch. You can create one with the following git command:

.. code-block:: console

    $ git checkout -b TOPIC-BRANCH

If you are working on a blueprint, name your :samp:`{TOPIC-BRANCH}`
``bp/BLUEPRINT`` where :samp:`{BLUEPRINT}` is the name of a blueprint in
Launchpad (for example, "bp/authentication"). The general convention when
working on bugs is to name the branch ``bug/BUG-NUMBER`` (for example,
"bug/1234567").

Read more about the commit syntax in the `Gerrit workflow`_ wiki.

.. _`Gerrit workflow`: https://docs.openstack.org/infra/manual/developers.html#development-workflow

Common problems
^^^^^^^^^^^^^^^

#. You realized that you were working in master and you haven't made any
   commits. Solution:

   .. code-block:: console

    $ git checkout -b newbranch
    $ git commit -a -m "Edited"

   If you already created the branch, omit the ``-b``.

   You put all your changes to :samp:`{newbranch}`. Problem solved.

#. You realized that you were working in master and you have made commits to
   master. Solution:

   .. code-block:: console

    $ git branch newbranch
    $ git reset --hard HEAD~x
    $ git checkout newbranch

   Where ``x`` is the number of commits you have made to master.
   And remember, you will lose any uncommitted work.

   You put your commits in :samp:`{newbranch}`. Problem solved.

#. You made multiple commits and realized that Gerrit requires one commit per
   patch. Solution:

   * You need to squash your previous commits. Make sure you are in your
     branch and follow `squashing guide`_. Then fill commit message properly.

   You squashed your commits. Problem solved.

Design principles
#################

Zaqar lives by the following design principles:

* `DRY`_
* `YAGNI`_
* `KISS`_

.. _`DRY`: https://en.wikipedia.org/wiki/Don%27t_repeat_yourself
.. _`YAGNI`: https://en.wikipedia.org/wiki/YAGNI
.. _`KISS`: https://en.wikipedia.org/wiki/KISS_principle

Try to stick to these design principles when working on your patch.

Test your code
##############

It is important to test your code and follow the python code style guidelines.
See :doc:`running_tests` for details on testing.

Submitting a patch
------------------

Once you finished coding your fix, add and commit your final changes.
Your commit message should:

* Provide a brief description of the change in the first line.
* Insert a single blank line after the first line.
* Provide a detailed description of the change in the following lines,
  breaking paragraphs where needed.
* The first line should be limited to 50 characters and should not end with a
  period.
* Subsequent lines should be wrapped at 72 characters.
* Put the 'Change-id', 'Closes-Bug #NNNNN' and 'blueprint NNNNNNNNNNN'
  lines at the very end.

Read more about `making a good commit message`_.

To submit it for review use the following git command:

.. code-block:: console

   $ git review

You will see the URL of your review page once it is successfully sent.

You can also see your reviews in :guilabel:`My Changes` in Gerrit. The first
thing to watch for is a ``+1`` in the :guilabel:`Verified` column next to your
patch in the server and/or client list of pending patches.

If the "Jenkins" user gives you a ``-1``, you'll need to check the log it posts
to find out what gate test failed, update your patch, and resubmit.

You can set your patch as a :guilabel:`work in progress` if your patch is
not ready to be merged, but you would still like some feedback from other
developers. To do this leave a review on your patch setting
:guilabel:`Workflow` to ``-1``.

Once the gate has verified your patch, other Zaqar developers will take a look
and submit their comments. When you get two or more ``+2``'s from core
reviewers, the patch will be approved and merged.

Don't be discouraged if a reviewer submits their comments with a ``-1``.
Patches iterate through several updates and reviews before they are ready for
merging.

To reply to feedback save all your comments as draft, then click on the
:guilabel:`Review` button. When replying to feedback, you as the patch
author can use the score of ``0``. The only exception to using the score of
``0`` is when you discover a blocking issue and you don't want your patch to
be merged. In which case, you can review your own patch with a ``-2``, while
you decide whether to keep, refactor, or withdraw the patch.

Professional conduct
--------------------

The Zaqar team holds reviewers accountable for promoting a positive,
constructive culture within our program.

If you ever feel that a reviewer is not acting professionally or is violating
the OpenStack community code of conduct, please let the PTL know immediately
so that he or she can help resolve the issue.

.. _`making a good commit message`: https://wiki.openstack.org/wiki/GitCommitMessages
.. _`squashing guide` : http://gitready.com/advanced/2009/02/10/squashing-commits-with-rebase.html
