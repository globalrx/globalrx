# Generated by Django 4.0.2 on 2023-04-01 05:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data', '0005_productsection_bert_vector'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productsection',
            name='bert_vector',
            field=models.TextField(blank=True, null=True),
        ),
    ]
