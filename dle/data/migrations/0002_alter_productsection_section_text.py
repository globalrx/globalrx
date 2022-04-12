
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE data_productsection ADD FULLTEXT INDEX `section_text` (`section_text`)",
            reverse_sql="ALTER TABLE data_productsection DROP INDEX `section_text`"
        )
    ]
