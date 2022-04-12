# Generated by Django 4.0.2 on 2022-04-12 17:54

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='DrugLabel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.CharField(choices=[('FDA', 'USA - Federal Drug Administration'), ('EMA', 'EU - European Medicines Agency'), ('USER-FDA', 'User-uploaded in FDA format'), ('USER-EMA', 'User-uploaded in EMA format')], db_index=True, max_length=8)),
                ('product_name', models.CharField(db_index=True, max_length=255)),
                ('generic_name', models.CharField(db_index=True, max_length=255)),
                ('version_date', models.DateField(db_index=True)),
                ('source_product_number', models.CharField(db_index=True, max_length=255)),
                ('raw_text', models.TextField()),
                ('marketer', models.CharField(db_index=True, max_length=255)),
                ('link', models.URLField()),
            ],
        ),
        migrations.CreateModel(
            name='LabelProduct',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('drug_label', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='data.druglabel')),
            ],
        ),
        migrations.CreateModel(
            name='ProductSection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('section_name', models.CharField(choices=[('INDICATIONS', 'Indications'), ('CONTRA', 'Contraindications'), ('WARN', 'Warnings'), ('PREG', 'Pregnancy'), ('POSE', 'Posology'), ('INTERACT', 'Interactions'), ('DRIVE', 'Effects on driving'), ('SIDE', 'Side effects'), ('OVER', 'Overdose')], db_index=True, max_length=255)),
                ('section_text', models.TextField()),
                ('label_product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='data.labelproduct')),
            ],
        ),
        migrations.AddConstraint(
            model_name='druglabel',
            constraint=models.UniqueConstraint(fields=('source', 'source_product_number', 'version_date'), name='unique_dl'),
        ),
    ]
