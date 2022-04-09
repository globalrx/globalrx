from django.db import models

from django.contrib.auth.models import AbstractUser
# Create your models here.
class User(AbstractUser):
    #this class consists of requested item as it is unique to each user
    pass 
