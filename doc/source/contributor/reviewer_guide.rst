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

==============
Reviewer Guide
==============

Overview
--------

Our program follows the usual OpenStack review process, albeit with some
important additions (see below). See also: :doc:`first_review`.

Be Professional
---------------
The PTL, with the support of the core reviewers, is ultimately responsible for
holding contributors accountable for creating a positive, constructive, and
productive culture. Inappropriate behavior will not be tolerated.
(`Why this is important?`_)

Do This:

* Act professionally.
* Treat others as friends and family.
* Seek first to understand.
* Be honest, transparent, and constructive.
* Use clear, concise language.
* Use prefixes to clarify the tone and intent of your comments.

Don't Do This:

* Use indecent, profane, or degrading language of any kind.
* Hold a patch hostage for an ulterior motive, political or otherwise.
* Abuse the review system to discuss big issues that would be better hashed out
  on the mailing list, in IRC, or during OpenStack Summit design sessions.
* Engage in bullying behaviors, including but not limited to:

  * Belittling others' opinions
  * Persistent teasing or sarcasm
  * Insulting, threatening, or yelling at someone
  * Accusing someone of being incompetent
  * Setting someone up to fail
  * Humiliating someone
  * Isolating someone from others
  * Withholding information to gain an advantage
  * Falsely accusing someone of errors
  * Sabotaging someone's work

Reviewing Docs
--------------

When possible, enlist the help of a professional technical writer to help
review each doc patch. All reviewers should familiarize themselves with
`OpenStack Documentation Contributor Guide`_. When reviewing user guide
patches, please run them through Maven and proof the resulting docs before
giving your ``+1`` or ``+2``.

Reviewing Code
--------------

When reviewing code patches, use your best judgment and seek to provide
constructive feedback to the author. Compliment them on things they have done
well, and highlight possible improvements. Also, dedicate as much time as
necessary in order to provide a careful analysis of the code. Don't assume that
someone else will catch any issues you yourself miss; in other words, pretend
you are the only person reviewing a given patch. Remember, "given enough
eyeballs, all bugs are shallow" ceases to be true the moment individual
reviewers become complacent.

Some things to check when reviewing code:

* Patch aligns with project goals, and is ideally associated with a bp or bug.
* Commit message is formatted appropriately and contains external references as
  needed.
* Coding style matches guidelines given in ``HACKING.rst``.
* Patch is cohesive and not too big to be reviewed in a timely manner (some
  patches may need to be split to improve cohesion and/or reduce size).
* Patch does what the commit message promises.
* Algorithms are implemented correctly, and chosen appropriately.
* Data schemas follow best practices.
* Unit and functional tests have been included and/or updated.
* Code contains no bugs (pay special attention to edge cases that tests may
  have missed).

Use Prefixes
------------

We encourage the use of prefixes to clarify the tone and intent of your review
comments. This is one way we try to mitigate misunderstandings that can lead to
bad designs, bad code, and bad blood.

.. list-table:: **Prefixes**
   :widths: 6 80 8
   :header-rows: 1

   * - Prefix
     - What the reviewer is saying
     - Blocker?
   * - KUDO
     - You did a nice job here, and I wanted to point that out. Keep up the
       good work!
     - No
   * - TEST
     - I think you are missing a test for this feature, code branch, specific
       data input, etc.
     - Yes
   * - BUG
     - I don't think this code does what it was intended to do, or I think
       there is a general design flaw here that we need to discuss.
     - Yes
   * - SEC
     - This is a serious security vulnerability and we better address it before
       merging the code.
     - Yes
   * - PERF
     - I have a concern that this won't be fast enough or won't scale. Let's
       discuss the issue and benchmark alternatives.
     - Yes
   * - DSQ
     - I think there is something critical here that we need to discuss this in
       IRC or on the mailing list before moving forward.
     - Yes
   * - STYLE
     - This doesn't seem to be consistent with other code and with
       ``HACKING.rst``
     - Yes
   * - Q
     - I don't understand something. Can you clarify?
     - Yes
   * - DRY
     - This could be modified to reduce duplication of code, data, etc.
       See also: `Wikipedia: Don't repeat yourself`_
     - Maybe
   * - YAGNI
     - This feature or flexibility probably isn't needed, or isn't worth the
       added complexity; if it is, we can always add the feature later. See
       also: `Wikipedia: You aren't gonna need it`_
     - Maybe
   * - NIT
     - This is a nitpick that I can live with if we want to merge without
       addressing it.
     - No
   * - IMO
     - I'm chiming in with my opinion in response to someone else's comment, or
       I just wanted to share an observation. Please take what I say with a
       grain of salt.
     - No
   * - FYI
     - I just wanted to share some useful information.
     - No

.. _`Why this is important?` : https://thoughtstreams.io/kgriffs/technical-communities/5060/
.. _`OpenStack Documentation Contributor Guide` : https://docs.openstack.org/contributor-guide/index.html
.. _`Wikipedia: Don't repeat yourself` : https://en.wikipedia.org/wiki/Don't_repeat_yourself
.. _`Wikipedia: You aren't gonna need it` : https://en.wikipedia.org/wiki/Don't_repeat_yourself
