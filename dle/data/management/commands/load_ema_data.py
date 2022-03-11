from django.core.management.base import BaseCommand, CommandError
from data.models import DrugLabel

# runs with `python manage.py load_ema_data`
class Command(BaseCommand):
    help = 'Loads data from EMA'

    def handle(self, *args, **options):
        # For now, just loading one dummy-label
        new_drug_label = DrugLabel(label_source='EMA', label_raw='Fake raw label text', label_date='2022-03-11')
        new_drug_label.save()

        self.stdout.write(self.style.SUCCESS('Success'))
