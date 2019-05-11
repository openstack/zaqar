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

=================
Your first review
=================

The review stage is a very important part in the development process. Following
are some of the reasons this stage is important:

* Getting other developers feedback minimizes the risk of adding
  regressions to the code base and ensures the quality of the code being
  merged.
* Building the community encourages everyone to review code. Everyone
  appreciates having their code reviewed.
* Since developers are always learning from being exposed to the points of view
  of others, reviews help developers to improve their coding skills.
* Providing a review is a great way to become familiar with the code.

Everyone is encourages to review code. You don't need to know every detail of
the code base. You need to understand only what the code related to the fix
does.

Step by step
------------

Go to ``review.opendev.org`` and filter by `Open Zaqar fixes`_. Select a fix
from the list to review. Try to select an easy patch for your first review.
That will help you to gain some confidence. Download the patch to your local
repository and test it:

.. code-block:: console

   $ git review -d [review-id]

The :samp:`{review-id}` is the number in the URL (check the screenshot for more
details).

Example:

.. code-block:: console

   $ git review -d 92979

.. image:: images/zaqar_review_id.png
   :alt: Zaqar review id

This git command creates a branch with the author's name and enables you to
test the patch in your local environment.

* Inspect the code. Use all of the best programming practices you know as you
  review the code.
* Give code location feedback.
   Do you consider that some code should be better located in another place
   within the file, or maybe in another file? If so, suggest this in the
   review comment and score with a ``-1`` if you think that it's that
   important.
* Give code-style feedback.
   Do you think that the code structure could be improved? Keep the DRY,
   YAGNI and KISS principles in mind.
* Give grammar and orthography feedback. Many of our contributors are not
  native English speakers, so it is common to find some errors of this type.
* Make sure that:

  * The commit message is formatted appropriately.
     Check `Git Commit Messages`_ for more information on how you should
     write a git commit message.
  * The coding style matches guidelines given in ``HACKING.rst``.
  * The patch is not too big.
     You might need to split some patches to improve cohesion and/or reduce
     size.
  * The patch does what the commit message promises.
  * Unit and functional tests are included and/or updated.
* If during the inspection you see a specific line you would like to bring up
  to discussion in the final review, leave feedback as an inline comment in
  Gerrit. This will make the review process easier. You can also use
  prefixes described in :doc:`reviewer_guide` for Zaqar inline comments.
* Keep in mind the :doc:`reviewer_guide` and be respectful when leaving
  feedback.
* Hit the  	:guilabel:`Review` button in the web UI to publish your comments
  and assign a score.
* Things to consider when leaving a score:

  * You can score with a ``-1`` if you think that there are things to fix. We
    have to be careful to not stall the cycle just because a few nits, so
    downvoting also depends on the current stage of the development cycle
    and the severity of the flaw you see.
  * You can score with a "0" if you are the author of the fix and you want to
    respond to the reviewers comments, or if you are a reviewer and you want
    to point out some reminder for future developing (e.g. the deadline is
    the next day and the fix needs to be merged, but you want something to be
    improved).
  * You can score with ``+1`` if the fix works and you think that the code
    looks good, upvoting is your choice.
* Remember to leave any comment that you think is important in the comment
  form. When you are done, click :guilabel:`Publish Comments`.

For more details on how to do a review, check out the `Gerrit Workflow
Review section`_ document.

.. _`Open Zaqar fixes`: https://review.opendev.org/#/q/status:open+zaqar,n,z
.. _`Git Commit Messages`: https://wiki.openstack.org/wiki/GitCommitMessages
.. _`Gerrit Workflow Review section`: https://docs.openstack.org/infra/manual/developers.html#code-review


