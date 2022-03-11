from django.test import TestCase
from .models import DrugLabel

# Create your tests here.


class DrugLabelModelTests(TestCase):

    def test_can_insert_record(self):
        num_drug_labels = DrugLabel.objects.count()

        new_drug_label = DrugLabel(
            label_source='EMA',
            label_raw='Fake raw label text',
            label_date='2022-03-11',
        )

        new_drug_label.save()

        new_num_drug_labels = DrugLabel.objects.count()
        self.assertEqual(num_drug_labels + 1, new_num_drug_labels)