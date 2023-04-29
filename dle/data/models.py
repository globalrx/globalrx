import json

from django.db import models

from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField

from elasticsearch_django.models import (
    SearchDocumentManagerMixin,
    SearchDocumentMixin,
    SearchResultsQuerySet,
)


SOURCES = [
    ("FDA", "USA - Federal Drug Administration"),
    ("EMA", "EU - European Medicines Agency"),
    ("TGA", "AU - Therapeutic Goods Administration"),
    ("HC", "HC - Health Canada"),
]


# DRUG LABEL
class DrugLabel(models.Model):
    """Version-specific document for a medication from EMA, FDA or other source (e.g. user-uploaded)
    - can have multiple versions of the same medication (different version_date's)
    - medication may exist in multiple regions (source's)
    - A `DrugLabel` has one or more `LabelProduct`s
    - `LabelProduct`s then have multiple `ProductSection`s
    """

    # Store when the object was created and updated, so we can skip labels that were recently scraped
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # The label's source agency (e.g. FDA, EMA, etc.)
    source = models.CharField(max_length=8, choices=SOURCES, db_index=True)
    # The label's product name (e.g. "Tylenol")
    product_name = models.CharField(max_length=255, db_index=True)
    # The label's generic name (e.g. "acetaminophen")
    generic_name = models.CharField(max_length=2048, db_index=True)
    # The label's version date (e.g. "2020-01-01"); labels may have multiple versions
    version_date = models.DateField(db_index=True)
    # The label's product number. This is specific to the source, and the format varies by source agency.
    source_product_number = models.CharField(max_length=255, db_index=True)
    raw_text = models.TextField()
    # The label's marketer (e.g. "Johnson & Johnson"). Marketer is like the manufacturer, but technically the manufacturer can be different.
    marketer = models.CharField(max_length=255, db_index=True)
    # An external link to the source agency's website, typically to the PDF of the label but in some cases,
    # like OpenFDA, it may be to a higher-level overview of the label rather than the PDF itself.
    link = models.URLField()

    class Meta:
        constraints = [
            # add a unique constraint across this composite key to prevent duplicate entries
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

    def as_dict(self):
        return {
            "source": self.source,
            "product_name": self.product_name,
            "generic_name": self.generic_name,
            "version_date": self.version_date,
            "source_product_number": self.source_product_number,
            "marketer": self.marketer,
            "link": self.link,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "id": self.id,
        }


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

    # raw text before we standardize by agency; optional, as we didn't store it for original scrapes
    original_section_name_text = models.CharField(max_length=255, null=True, blank=True)

    # standardized section name, by agency
    section_name = models.CharField(max_length=255, db_index=True)

    # mapped metacategory for comparison across agengies
    section_metacategory = models.CharField(max_length=255, db_index=True)

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
            "section_metacategory": self.section_metacategory,
            "section_text": self.section_text,
            "id": str(self.id),
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
    ("data_error", "DataError"),
    ("no_pdf", "No PDF"),
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

    # Store when the error was created and when it was last parsed
    created_at = models.DateTimeField(auto_now_add=True)
    last_parsed = models.DateTimeField(auto_now=True)

    url = models.URLField(max_length=400, blank=False)
    source_product_number = models.CharField(max_length=100, blank=True)
    error_type = models.CharField(
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
