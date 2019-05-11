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

===================================
Continuous integration with Jenkins
===================================

Zaqar uses a `Jenkins`_ server to automate development tasks. The Jenkins
front-end is at http://jenkins.openstack.org. You must have an account on
`Launchpad`_ to be able to access the OpenStack Jenkins site.

Jenkins performs tasks such as running static code analysis, running unit
tests, and running functional tests.  For more details on the jobs being run by
Jenkins, see the code reviews on https://review.opendev.org. Tests are run
automatically and comments are put on the reviews automatically with the
results.

You can also get a view of the jobs that are currently running from the Zuul
status dashboard, http://zuul.openstack.org/.

.. _Jenkins: http://jenkins-ci.org
.. _Launchpad: http://launchpad.net
