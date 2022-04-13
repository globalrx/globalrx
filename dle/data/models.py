from django.db import models

# Create your models here. Then run:
# `python manage.py makemigrations`
# `python manage.py migrate`

SOURCES = [
    ("FDA", "USA - Federal Drug Administration"),
    ("EMA", "EU - European Medicines Agency"),
]

SECTION_NAMES = [
    ("Indications", "Indications"),
    ("Contraindications", "Contraindications"),
    ("Warnings", "Warnings"),
    ("Pregnancy", "Pregnancy"),
    ("Posology", "Posology"),
    ("Interactions", "Interactions"),
    ("Effects on driving", "Effects on driving"),
    ("Side effects", "Side effects"),
    ("Overdose", "Overdose"),
]
"This is a WIP"


class DrugLabelBase(models.Model):
    label_id = models.CharField(max_length=255)
    "label_id is: (source + version_date + product_name)[:255]"
    source = models.CharField(max_length=8)
    "e.g. EMA, FDA"
    product_name = models.CharField(max_length=255)
    "The name of the medicine (brand name)"
    version_date = models.DateField()
    "The date the label was submitted (or maybe approved)"
    generic_name = models.CharField(max_length=255)
    "The generic name of the medicine"  # TODO this can have multiple entries, should be a many to one
    source_product_number = models.CharField(max_length=255)
    "source-specific product-id"
    marketer = models.CharField(max_length=255)
    "marketer is 'like' the manufacturer, but technically the manufacturer can be different"

    def set_label_id(self):
        self.label_id = (self.source + self.version_date + self.product_name)[:255]

    def save(self, *args, **kwargs):
        self.set_label_id()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"source: {self.source}, "
            f"product_name: {self.product_name}, "
            f"version_date: {self.version_date}, "
            f"label_id: {self.label_id}, "
        )

    class Meta:
        abstract = True


class DrugLabel(DrugLabelBase):
    """
    Using ColumnStore for DrugLabel, so cannot have Keys/Indexes.
    Using label_id as a string-id to tie to InnoDB tables
    """

    @staticmethod
    def from_child(drug_label_doc):
        dl = DrugLabel()
        dl.label_id = drug_label_doc.label_id
        dl.source = drug_label_doc.source
        dl.product_name = drug_label_doc.product_name
        dl.version_date = drug_label_doc.version_date
        dl.generic_name = drug_label_doc.generic_name
        dl.source_product_number = drug_label_doc.source_product_number
        dl.marketer = drug_label_doc.marketer
        return dl


class DrugLabelDoc(DrugLabelBase):
    """Version-specific document for a medication from EMA, FDA or other source (e.g. user-uploaded)
    - can have multiple versions of the same medication (different version_date's)
    - medication may exist in multiple regions (source's)
    - A `DrugLabel` has one or more `LabelProduct`s
    - `LabelProduct`s then have multiple `ProductSection`s
    """

    link = models.URLField()
    "link is url to the external data source website"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source", "source_product_number", "version_date"],
                name="unique_dl",
            )
        ]


class DrugLabelRawText(models.Model):
    """Storing the raw_text in a separate table as it likely will not be used."""

    drug_label = models.ForeignKey(DrugLabelDoc, on_delete=models.CASCADE)
    raw_text = models.TextField()


class LabelProduct(models.Model):
    """A `DrugLabel` may have multiple `LabelProduct`s.
    These are typically for different routes of administration for the medication.
    """

    drug_label = models.ForeignKey(DrugLabelDoc, on_delete=models.CASCADE)


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
