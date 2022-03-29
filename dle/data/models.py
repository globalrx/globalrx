from django.db import models

# Create your models here. Then run:
# `python manage.py makemigrations`
# `python manage.py migrate`

SOURCES = [
    ("FDA", "USA - Federal Drug Administration"),
    ("EMA", "EU - European Medicines Agency"),
    ("USER-FDA", "User-uploaded in FDA format"),
    ("USER-EMA", "User-uploaded in EMA format"),
]

SECTION_NAMES = [
    ("INDICATIONS", "Indications"),
    ("CONTRA", "Contraindications"),
    ("WARN", "Warnings"),
    ("PREG", "Pregnancy"),
    ("POSE", "Posology"),
    ("INTERACT", "Interactions"),
    ("DRIVE", "Effects on driving"),
    ("SIDE", "Side effects"),
    ("OVER", "Overdose"),
]
"This is a WIP"


class DrugLabel(models.Model):
    """Version-specific document for a medication from EMA, FDA or other source (e.g. user-uploaded)
    - can have multiple versions of the same medication (different version_date's)
    - medication may exist in multiple regions (source's)
    - A `DrugLabel` has one or more `LabelProduct`s
    - `LabelProduct`s then have multiple `ProductSection`s
    """

    source = models.CharField(max_length=8, choices=SOURCES, db_index=True)
    product_name = models.CharField(max_length=255, db_index=True)
    generic_name = models.CharField(max_length=255, db_index=True)
    version_date = models.DateField(db_index=True)
    source_product_number = models.CharField(max_length=255, db_index=True)
    "source-specific product-id"
    raw_text = models.TextField()
    marketer = models.CharField(max_length=255, db_index=True)
    "marketer is 'like' the manufacturer, but technically the manufacturer can be different"
    link = models.URLField()
    "link is url to the external data source website"

    class Meta:
        constraints = [
            # add a unique constraint to prevent duplicate entries
            models.UniqueConstraint(fields=["source", "source_product_number", "version_date"], name="unique_dl")
        ]

    def __str__(self):
        return (
            f"source: {self.source}, "
            f"product_name: {self.product_name}, "
            f"generic_name: {self.generic_name}, "
            f"version_date: {self.version_date}, "
            f"source_product_number: {self.source_product_number}, "
            f"raw_text: {self.raw_text[0:10]}..., "
            f"marketer: {self.marketer}"
        )


class LabelProduct(models.Model):
    """A `DrugLabel` may have multiple `LabelProduct`s.
    These are typically for different routes of administration for the medication.
    """

    drug_label = models.ForeignKey(DrugLabel, on_delete=models.CASCADE)


class ProductSection(models.Model):
    """There are multiple `ProductSection`s for each `LabelProduct`.
    The original sections vary by DrugLabel->source.
    We attempt to standardize them
    """

    label_product = models.ForeignKey(LabelProduct, on_delete=models.CASCADE)
    section_name = models.CharField(
        max_length=255, choices=SECTION_NAMES, db_index=True
    )
    section_text = models.TextField()
