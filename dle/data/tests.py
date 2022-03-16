from django.test import TestCase
from .models import DrugLabel, LabelProduct, ProductSection

# Create your tests here.

# runs with `python manage.py test data`
class DrugLabelModelTests(TestCase):

    def test_can_insert_drug_label(self):
        num_entries = DrugLabel.objects.count()

        dl = DrugLabel(
            source='EMA',
            product_name='Diffusia',
            generic_name='lorem ipsem',
            version_date='2022-03-15',
            source_product_number='ABC-123-DO-RE-ME',
            raw_text='Fake raw label text',
            marketer='Landau Pharma',
        )
        dl.save()

        new_num_entries = DrugLabel.objects.count()
        self.assertEqual(num_entries + 1, new_num_entries)

    def test_can_insert_label_product(self):
        dl = DrugLabel(
            source='EMA',
            product_name='Diffusia',
            generic_name='lorem ipsem',
            version_date='2022-03-15',
            source_product_number='ABC-123-DO-RE-ME',
            raw_text='Fake raw label text',
            marketer='Landau Pharma',
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
            source='EMA',
            product_name='Diffusia',
            generic_name='lorem ipsem',
            version_date='2022-03-15',
            source_product_number='ABC-123-DO-RE-ME',
            raw_text='Fake raw label text',
            marketer='Landau Pharma',
        )
        dl.save()
        lp = LabelProduct(drug_label=dl)
        lp.save()
        ps = ProductSection(
            label_product=lp,
            section_name='INDICATIONS',
            section_text='Cures cognitive deficit disorder'
        )
        ps.save()
        ps = ProductSection(
            label_product=lp,
            section_name='WARN',
            section_text='May cause x, y, z'
        )
        ps.save()
        ps = ProductSection(
            label_product=lp,
            section_name='PREG',
            section_text='Good to go'
        )
        ps.save()

        # we added 3 ProductSections
        new_num_entries = ProductSection.objects.count()
        self.assertEqual(num_entries + 3, new_num_entries)

    def test_can_insert_skilarence(self):
        """Verify that we can get the correct values from the pdf"""
        dl = DrugLabel(
            source='EMA',
            product_name='Skilarence',
            generic_name='dimethyl fumarate',
            version_date='2022-03-08', # EU formats date differently
            source_product_number='EMEA/H/C/002157',
            raw_text='Ignore for now',
            marketer='Almirall S.A',
        )
        dl.save()
        lp = LabelProduct(drug_label=dl)
        lp.save()
        ps = ProductSection(
            label_product=lp,
            section_name='INDICATIONS',
            section_text=('Skilarence is indicated for the treatment of moderate'
                          ' to severe plaque psoriasis in adults in need of systemic medicinal'
                          ' therapy.'
                          )
        )
        ps.save()

        # verify the fields match
        # TODO WIP, need to get it parsed

