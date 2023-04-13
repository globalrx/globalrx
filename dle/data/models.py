import json

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
    ("TGA", "AU - Therapeutic Goods Administration"),
]


# DRUG LABEL
class DrugLabel(models.Model):
    """Version-specific document for a medication from EMA, FDA or other source (e.g. user-uploaded)
    - can have multiple versions of the same medication (different version_date's)
    - medication may exist in multiple regions (source's)
    - A `DrugLabel` has one or more `LabelProduct`s
    - `LabelProduct`s then have multiple `ProductSection`s
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    source = models.CharField(max_length=8, choices=SOURCES, db_index=True)
    product_name = models.CharField(max_length=255, db_index=True)
    generic_name = models.CharField(max_length=2048, db_index=True)
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


# LABEL PRODUCT
class LabelProduct(models.Model):
    """A `DrugLabel` may have multiple `LabelProduct`s.
    These are typically for different routes of administration for the medication.
    """

    drug_label = models.ForeignKey(DrugLabel, on_delete=models.CASCADE)


# PRODUCT SECTION
# Includes Elasticsearch mapping; some data from DrugLabel is denormalized and added here too
# See: https://github.com/yunojuno/elasticsearch-django/blob/master/tests/models.py
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
    # TODO can remove this once we deprecate PSQL based search
    search_vector = SearchVectorField(null=True)

    objects = ProductSectionModelManager.from_queryset(ProductSectionQuerySet)()

    # bert_vector will never be accessed directly, only pre-computed, stored, and added to Elasticsearch as a dense_vector field
    # The vectorization function produces an np.ndarray which we turn into a list and serialize with json.dumps()
    # The resulting jsonified list is stored here, then deserialized in as_search_document() for ingest
    bert_vector = models.TextField(blank=True, null=True)

    class Meta:
        indexes = (GinIndex(fields=["search_vector"]),)

    def as_search_document(self, index="_all") -> dict:
        """Converts a ProductSection into a Elasticsearch document.
        Includes many fields from the related DrugLabel.
        Returns:
            dict: Search document
        """
        # TODO if we do not need any of these fields for search (e.g. only needed for display on a template page), then we can remove them here to save ES index space
        return {
            "label_product_id": self.label_product.id,
            "drug_label_id": self.label_product.drug_label.id,
            "drug_label_product_name": DrugLabel.objects.get(
                id=self.label_product.drug_label.id
            ).product_name,
            "drug_label_source": DrugLabel.objects.get(id=self.label_product.drug_label.id).source,
            "drug_label_generic_name": DrugLabel.objects.get(
                id=self.label_product.drug_label.id
            ).generic_name,
            "drug_label_version_date": DrugLabel.objects.get(
                id=self.label_product.drug_label.id
            ).version_date,
            "drug_label_source_product_number": DrugLabel.objects.get(
                id=self.label_product.drug_label.id
            ).source_product_number,
            "drug_label_marketer": DrugLabel.objects.get(
                id=self.label_product.drug_label.id
            ).marketer,
            "drug_label_link": DrugLabel.objects.get(id=self.label_product.drug_label.id).link,
            "section_name": self.section_name,
            "section_text": self.section_text,
            "id": str(self.id),
            # "text_embedding": np.empty() if not self.bert_vector else np.array(json.loads(self.bert_vector)),
            "text_embedding": []
            if not self.bert_vector
            else [float(w) for w in json.loads(self.bert_vector)],
        }

    # TODO - implement for partial updates?
    # def as_search_document_update(self, index, update_fields):
    #     if 'user' in update_fields:
    #         # remove so that it won't raise a ValueError
    #         update_fields.remove('user')
    #         doc = super().as_search_document_update(index, update_fields)
    #         doc['user'] = self.user.get_full_name()
    #         return doc
    #     return super().as_search_document_update(index, update_fields)

    def get_search_queryset(self, index="_all"):
        return self.get_queryset()


PARSING_ERROR_TYPES = [
    ("version_date_empty", "Version date empty"),
    ("version_date_parse", "Version date parsed failure"),
    ("pdf_error", "Failed to parse PDF"),
    ("link_error", "Could not generate PDF link"),
]

AGENCY_CHOICES = [
    ("TGA", "Therapeutic Goods Administration"),
    ("FDA", "Food and Drug Administration"),
    ("EMA", "European Medicines Agency"),
]


class ParsingError(models.Model):
    """
    Class to track known DrugLabel parsing errors for further improvements
    """

    created_at = models.DateTimeField(auto_now_add=True)
    last_parsed = models.DateTimeField(auto_now=True)
    url = models.URLField(max_length=400, blank=False)
    errorType = models.CharField(
        max_length=30,
        choices=PARSING_ERROR_TYPES,
        default=None,
        blank=True,
    )
    source = models.CharField(
        max_length=10,
        choices=AGENCY_CHOICES,
        default=None,
        blank=True,
    )
    message = models.TextField(blank=True)
    # maybe it's possible to have a partial parsing error for a label that is good enough to save
    label = models.ForeignKey(
        DrugLabel,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"{self.url}: last parsed at {self.last_parsed.strftime('%m/%d/%Y, %H:%M:%S')}"
