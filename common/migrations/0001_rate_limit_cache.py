"""
Create the DatabaseCache table used by the rate limit middleware.

The table is normally created with `manage.py createcachetable`, which does not
run as part of `manage.py migrate`. Creating it here guarantees it exists on
every deployed database, including serverless environments.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.RunSQL(
            sql=[
                (
                    'CREATE TABLE IF NOT EXISTS "rate_limit_cache" ('
                    '    "cache_key" varchar(255) NOT NULL PRIMARY KEY,'
                    '    "value" text NOT NULL,'
                    '    "expires" timestamp with time zone NOT NULL'
                    ');'
                ),
                (
                    'CREATE INDEX IF NOT EXISTS "rate_limit_cache_expires" '
                    'ON "rate_limit_cache" ("expires");'
                ),
            ],
            reverse_sql='DROP TABLE "rate_limit_cache";',
        ),
    ]