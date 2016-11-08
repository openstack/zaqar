<!--
Copyright 2012 New Dream Network, LLC (DreamHost)

Licensed under the Apache License, Version 2.0 (the "License"); you may
not use this file except in compliance with the License. You may obtain
a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations
under the License.
-->

The migrations in `alembic_migrations/versions` contain the changes needed to migrate
between Zaqar database revisions. A migration occurs by executing a script that
details the changes needed to upgrade the database. The migration scripts
are ordered so that multiple scripts can run sequentially. The scripts are executed by
Zaqar's migration wrapper which uses the Alembic library to manage the migration. Zaqar
supports migration from Liberty or later.

You can upgrade to the latest database version via:
```
$ zaqar-sql-db-manage --config-file /path/to/zaqar.conf upgrade head
```

To check the current database version:
```
$ zaqar-sql-db-manage --config-file /path/to/zaqar.conf current
```

To create a script to run the migration offline:
```
$ zaqar-sql-db-manage --config-file /path/to/zaqar.conf upgrade head --sql
```

To run the offline migration between specific migration versions:
```
$ zaqar-sql-db-manage --config-file /path/to/zaqar.conf upgrade <start version>:<end version> --sql
```

Upgrade the database incrementally:
```
$ zaqar-sql-db-manage --config-file /path/to/zaqar.conf upgrade --delta <# of revs>
```

Create new revision:
```
$ zaqar-sql-db-manage --config-file /path/to/zaqar.conf revision -m "description of revision" --autogenerate
```

Create a blank file:
```
$ zaqar-sql-db-manage --config-file /path/to/zaqar.conf revision -m "description of revision"
```

This command does not perform any migrations, it only sets the revision.
Revision may be any existing revision. Use this command carefully.
```
$ zaqar-sql-db-manage --config-file /path/to/zaqar.conf stamp <revision>
```

To verify that the timeline does branch, you can run this command:
```
$ zaqar-sql-db-manage --config-file /path/to/zaqar.conf check_migration
```

If the migration path does branch, you can find the branch point via:
```
$ zaqar-sql-db-manage --config-file /path/to/zaqar.conf history
```
