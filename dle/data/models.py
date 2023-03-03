from django.db import models
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from elasticsearch_django.models import (
    SearchDocumentManagerMixin,
    SearchDocumentMixin,
    SearchResultsQuerySet,
)

# Create your models here. Then run:
# `python manage.py makemigrations`
# `python manage.py migrate`

SOURCES = [
    ("FDA", "USA - Federal Drug Administration"),
    ("EMA", "EU - European Medicines Agency"),
]

### DRUG LABEL ###
# See: https://github.com/yunojuno/elasticsearch-django/blob/master/tests/models.py
class DrugLabelQuerySet(SearchResultsQuerySet):
    pass

class DrugLabelModelManager(SearchDocumentManagerMixin, models.Manager):
    def get_search_queryset(self, index="_all"):
        return self.all()

class DrugLabel(SearchDocumentMixin,models.Model):
# class DrugLabel(models.Model):
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

    objects = DrugLabelModelManager.from_queryset(DrugLabelQuerySet)()

    class Meta:
        constraints = [
            # add a unique constraint to prevent duplicate entries
            models.UniqueConstraint(
                fields=["source", "source_product_number", "version_date"],
                name="unique_dl",
            )
        ]

    def __str__(self):
        return (
            f"source: {self.source}, "
            f"product_name: {self.product_name}, "
            f"generic_name: {self.generic_name}, "
            f"version_date: {self.version_date}, "
            f"source_product_number: {self.source_product_number}, "
            f"marketer: {self.marketer}"
        )
    
    def as_search_document(self, index="_all") -> dict:
        """Converts a DrugLabel into a search document.
        Returns:
            dict: Search document
        """
        return {
            "source": self.source,
            "product_name": self.product_name,
            "generic_name": self.generic_name,
            "version_date": self.version_date,
            "source_product_number": self.source_product_number,
            "marketer": self.marketer,
            "link": self.link,
            "raw_text": self.raw_text,
        }
    
    # def as_search_document_update(self, index, update_fields):
    #     if 'user' in update_fields:
    #         # remove so that it won't raise a ValueError
    #         update_fields.remove('user')
    #         doc = super().as_search_document_update(index, update_fields)
    #         doc['user'] = self.user.get_full_name()
    #         return doc
    #     return super().as_search_document_update(index, update_fields)

    def get_search_queryset(self, index='_all'):
        return self.get_queryset()

#### LABEL PRODUCT ####
class LabelProduct(models.Model):
    """A `DrugLabel` may have multiple `LabelProduct`s.
    These are typically for different routes of administration for the medication.
    """

    drug_label = models.ForeignKey(DrugLabel, on_delete=models.CASCADE)

### PRODUCT SECTION ###
class ProductSectionQuerySet(SearchResultsQuerySet):
    pass

class ProductSectionModelManager(SearchDocumentManagerMixin, models.Manager):
    def get_search_queryset(self, index="_all"):
        return self.all()

# class ProductSection(models.Model):
class ProductSection(SearchDocumentMixin, models.Model):
    """There are multiple `ProductSection`s for each `LabelProduct`.
    The original sections vary by DrugLabel->source.
    We attempt to standardize them
    """

    label_product = models.ForeignKey(LabelProduct, on_delete=models.CASCADE)
    section_name = models.CharField(max_length=255, db_index=True)
    section_text = models.TextField()

    # https://fueled.com/the-cache/posts/backend/django/setup-full-text-search-index-in-django/
    # TODO can probably remove this once we deprecate PSQL based search?
    search_vector = SearchVectorField(null=True)

    objects = ProductSectionModelManager.from_queryset(ProductSectionQuerySet)()

    class Meta:
        indexes = (GinIndex(fields=["search_vector"]),)
    
    def as_search_document(self, index="_all") -> dict:
        """Converts a ProductSection into a Elasticsearch document.
        Returns:
            dict: Search document
        """
        return {
            "label_product_id": self.label_product.id,
            "drug_label_id": self.label_product.drug_label.id,
            "drug_label_name": DrugLabel.objects.get(id=self.label_product.drug_label.id).product_name,
            "section_name": self.section_name,
            "section_text": self.section_text,
            "id": self.id,
        }
    
    def get_search_queryset(self, index='_all'):
        return self.get_queryset()