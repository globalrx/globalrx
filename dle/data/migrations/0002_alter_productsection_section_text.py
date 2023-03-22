from django.db import migrations, models
from django.contrib.postgres.search import SearchVector
import django.contrib.postgres.indexes
import django.contrib.postgres.search

def compute_search_vector(apps, schema_editor):
    ProductSection = apps.get_model("data", "ProductSection")
    ProductSection.objects.update(search_vector=SearchVector("section_text"))


class Migration(migrations.Migration):

    dependencies = [
        ("data", "0001_initial"),
    ]

    # operations = [
    #     migrations.RunSQL(
    #         sql="ALTER TABLE data_productsection ADD FULLTEXT INDEX `section_text` (`section_text`)",
    #         reverse_sql="ALTER TABLE data_productsection DROP INDEX `section_text`",
    #     )
    # ]

    operations = [
        migrations.AddField(
            model_name='productsection',
            name='search_vector',
            field=django.contrib.postgres.search.SearchVectorField(null=True),
        ),
        migrations.AddIndex(
            model_name='productsection',
            index=django.contrib.postgres.indexes.GinIndex(fields=['search_vector'], name='data_produc_search__727e3f_gin'),
        ),
        migrations.RunSQL(
            sql="""
            CREATE TRIGGER search_vector_trigger
            BEFORE INSERT OR UPDATE OF section_text, search_vector
            ON data_productsection
            FOR EACH ROW EXECUTE PROCEDURE
            tsvector_update_trigger(
                search_vector, 'pg_catalog.english', section_text
            );
            UPDATE data_productsection SET search_vector = NULL;
            """,
            reverse_sql="""
            DROP TRIGGER IF EXISTS search_vector_trigger
            ON data_productsection;
            """,
        ),
        migrations.RunPython(
            compute_search_vector, reverse_code=migrations.RunPython.noop
        ),
    ]
