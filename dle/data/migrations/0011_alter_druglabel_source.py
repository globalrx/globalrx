# Generated by Django 4.2 on 2023-04-19 13:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data', '0010_rename_errortype_parsingerror_error_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='druglabel',
            name='source',
            field=models.CharField(choices=[('FDA', 'USA - Federal Drug Administration'), ('EMA', 'EU - European Medicines Agency'), ('TGA', 'AU - Therapeutic Goods Administration'), ('HC', 'HC - Health Canada')], db_index=True, max_length=8),
        ),
    ]
