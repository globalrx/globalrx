from django.db import models

from django.contrib.auth.models import AbstractUser

from data.models import DrugLabel


class User(AbstractUser):
    pass


class MyLabel(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    drug_label = models.ForeignKey(DrugLabel, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, db_index=True)
    file = models.FileField(upload_to="my_labels/", max_length=255)
    is_successfully_parsed = models.BooleanField(default=False, db_index=True)

    def __str__(self):
        return (
            f"MyLabel: {self.id}, "
            f"user: {self.user}, "
            f"drug_label: {self.drug_label}, "
            f"name: {self.name}, "
            f"file.name: {self.file.name}, "
            f"is_successfully_parsed: {self.is_successfully_parsed}"
        )

class SavedSearch(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    url = models.TextField()
    name = models.CharField(max_length=255, db_index=True)

