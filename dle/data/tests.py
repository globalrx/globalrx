from django.db import IntegrityError
from django.test import TestCase
from .models import DrugLabel, LabelProduct, ProductSection
from django.core import management


# Create your tests here.

# runs with `python manage.py test data`
class DrugLabelModelTests(TestCase):
    def test_can_insert_drug_label(self):
        num_entries = DrugLabel.objects.count()

        dl = DrugLabel(
            source="EMA",
            product_name="Diffusia",
            generic_name="lorem ipsem",
            version_date="2022-03-15",
            source_product_number="ABC-123-DO-RE-ME",
            raw_text="Fake raw label text",
            marketer="Landau Pharma",
        )
        dl.save()

        new_num_entries = DrugLabel.objects.count()
        self.assertEqual(num_entries + 1, new_num_entries)

    def test_can_insert_label_product(self):
        dl = DrugLabel(
            source="EMA",
            product_name="Diffusia",
            generic_name="lorem ipsem",
            version_date="2022-03-15",
            source_product_number="ABC-123-DO-RE-ME",
            raw_text="Fake raw label text",
            marketer="Landau Pharma",
        )
        dl.save()

        num_entries = LabelProduct.objects.count()

        lp = LabelProduct(drug_label=dl)
        lp.save()

        new_num_entries = LabelProduct.objects.count()
        self.assertEqual(num_entries + 1, new_num_entries)

    def test_can_insert_product_section(self):
        num_entries = ProductSection.objects.count()
        dl = DrugLabel(
            source="EMA",
            product_name="Diffusia",
            generic_name="lorem ipsem",
            version_date="2022-03-15",
            source_product_number="ABC-123-DO-RE-ME",
            raw_text="Fake raw label text",
            marketer="Landau Pharma",
        )
        dl.save()
        lp = LabelProduct(drug_label=dl)
        lp.save()
        ps = ProductSection(
            label_product=lp,
            section_name="INDICATIONS",
            section_text="Cures cognitive deficit disorder",
        )
        ps.save()
        ps = ProductSection(
            label_product=lp, section_name="WARN", section_text="May cause x, y, z"
        )
        ps.save()
        ps = ProductSection(
            label_product=lp, section_name="PREG", section_text="Good to go"
        )
        ps.save()

        # we added 3 ProductSections
        new_num_entries = ProductSection.objects.count()
        self.assertEqual(num_entries + 3, new_num_entries)

    def test_load_ema_data(self):
        num_dl_entries = DrugLabel.objects.count()
        management.call_command("load_ema_data", type="test")
        # should insert 3 dl records
        num_new_dl_entries = DrugLabel.objects.count()
        self.assertEqual(num_dl_entries + 3, num_new_dl_entries)

    def test_can_insert_skilarence(self):
        """Verify that we can get the correct values from the pdf"""
        management.call_command("load_ema_data", type="test")
        dl = DrugLabel(
            source="EMA",
            product_name="Skilarence",
            generic_name="dimethyl fumarate",
            version_date="2022-03-08",  # EU formats date differently
            source_product_number="EMEA/H/C/002157",
            marketer="Almirall S.A",
        )
        dl_saved = DrugLabel.objects.filter(product_name="Skilarence").all()[:1].get()
        # verify the fields match
        self.assertEqual(dl.source, dl_saved.source)
        self.assertEqual(dl.generic_name, dl_saved.generic_name)
        # model returns date as datetime.date object, convert to string for comparison
        self.assertEqual(dl.version_date, dl_saved.version_date.strftime("%Y-%m-%d"))
        self.assertEqual(dl.source_product_number, dl_saved.source_product_number)
        self.assertEqual(dl.marketer, dl_saved.marketer)

    def test_unique_constraint(self):
        """Unique constraint on DrugLabel should prevent us from adding
        entries where all of the following are identical:
        source, source_product_number, version_date

        """
        dl = DrugLabel(
            source="EMA",
            source_product_number="Fake-1",
            version_date="2022-03-08",
        )
        dl.save()

        dl2 = DrugLabel(
            source="EMA",
            source_product_number="Fake-1",
            version_date="2022-03-08",
        )
        # this second save raises a django.db.utils.IntegrityError
        with self.assertRaises(IntegrityError):
            dl2.save()

    def test_raw_text_is_saved(self):
        """Verify that we can get the correct values from the pdf"""
        management.call_command("load_ema_data", type="test")
        dl_saved = DrugLabel.objects.filter(product_name="Skilarence").all()[:1].get()
        self.assertGreater(
            len(dl_saved.raw_text),
            100,
            f"len(dl_saved.raw_text) was only: {len(dl_saved.raw_text)}",
        )

    # def test_load_ema_data_full(self):
    #     num_dl_entries = DrugLabel.objects.count()
    #     management.call_command("load_ema_data", type="full", verbosity=2)
    #     # should insert over 1200 dl records
    #     num_new_dl_entries = DrugLabel.objects.count()
    #     self.assertGreater(num_new_dl_entries, num_dl_entries + 1000)

    # def test_ema_data_query_1(self):
    #     q_marketer = "pfizer"
    #     labels = DrugLabel.objects\
    #         .filter(marketer__icontains=q_marketer)\
    #         .filter(source='EMA')\
    #         .all()
    #     self.assertEqual(labels.count(), 53)

    # def test_ema_data_query_2(self):
        # see how many matches
        # from data.models import DrugLabel, LabelProduct, ProductSection
        # q_marketer = "pfizer"
        # q_section_name = "INDICATIONS"
        # q_section_text = 'kidney'
        # qs = ProductSection.objects \
        #     .filter(label_product__drug_label__marketer__icontains=q_marketer) \
        #     .defer("label_product__drug_label__raw_text") \
        #     .filter(section_text__icontains=q_section_text)\
        #     .filter(section_name=q_section_name)\
        #     .all()
        # # note: count(), doesn't evaluate the queryset
        # # len() and list() force the queryset to evaluate
        # num_results = len(qs)
        # print(f"num_results: {num_results}")
        # # 5
        # for ps in qs:
        #     lp = ps.label_product
        #     dl = lp.drug_label
        #     print("")
        #     print(f"product_name: {dl.product_name}")
        #     print(f"marketer: {dl.marketer}")
        #     print(f"version_date: {dl.version_date}")
        #     print(f"section_text: {ps.section_text[0:200]}")
        #
        # # 'reverse' has no underbars in the model-name
        # qs = DrugLabel.objects \
        #     .filter(marketer__icontains=q_marketer)\
        #     .filter(labelproduct__productsection__section_text__icontains=q_section_text)\
        #     .filter(labelproduct__productsection__section_name=q_section_name) \
        #     .defer("raw_text")\
        #     .distinct()\
        #     .all()
        # num_results = len(qs)
        # print(f"num_results: {num_results}")
        # # 16 ... 12 ... there are duplicate results
        # for dl in qs:
        #     lp = dl.labelproduct_set.all()[0]
        #     ps = lp.productsection_set.all()[0]
        #     print("")
        #     print(f"product_name: {dl.product_name}")
        #     print(f"marketer: {dl.marketer}")
        #     print(f"version_date: {dl.version_date}")
        #     print(f"section_text: {ps.section_text[0:200]}")

        # from data.models import DrugLabel, LabelProduct, ProductSection
        # qs = DrugLabel.objects.filter(product_name='Lidorex').all()
        # num_results = len(qs)
        # print(f"num_results: {num_results}")
        # for dl in qs:
        #     print("")
        #     print(f"product_name: {dl.product_name}")
        #     print(f"marketer: {dl.marketer}")
        #     print(f"version_date: {dl.version_date}")
        #     try:
        #         lp = dl.labelproduct_set.all()[0]
        #         ps = lp.productsection_set.all()[0]
        #         print(f"section_name: {ps.section_name}")
        #         print(f"section_text: {ps.section_text[0:200]}")
        #     except:
        #         pass

        # pass

    def test_load_fda_data(self):
        num_dl_entries = DrugLabel.objects.count()
        management.call_command("load_fda_data", type="test")
        # should insert at least 1 dl records
        num_new_dl_entries = DrugLabel.objects.count()
        self.assertGreater(num_new_dl_entries, num_dl_entries)
