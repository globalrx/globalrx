from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("data", "0001_initial"),
        ("data", "0002_alter_productsection_section_text"),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE data_druglabel MODIFY id BIGINT NOT NULL;",
            reverse_sql="ALTER TABLE data_druglabel MODIFY id BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE data_druglabel DROP PRIMARY KEY;",
            reverse_sql="ALTER TABLE data_druglabel ADD CONSTRAINT pk PRIMARY KEY (id);",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE data_druglabel ENGINE=ColumnStore;",
            reverse_sql="ALTER TABLE data_druglabel ENGINE=INNODB;",
        ),
    ]
