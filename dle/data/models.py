from django.db import models

# Create your models here.


class DrugLabel(models.Model):
    LABEL_SOURCES = [
        ('FDA', 'USA - Federal Drug Administration'),
        ('EMA', 'EU - European Medicines Agency'),
    ]
    label_source = models.CharField(max_length=3, choices=LABEL_SOURCES, db_index=True)
    label_raw = models.TextField()
    label_date = models.DateField(db_index=True)
