from urllib import response
from django.test import TestCase
from django.contrib.auth.models import User

# Create your tests here.
class User_tests(TestCase):
    def test_dummy(self):
        self.assertEqual(1, 1)



    def test_register_users(self):
        response = self.user
        self.assertEqual(response.status_code,302)

    def test_register_page(self):
        response = self.register_url
        self.assertEqual(response.status_code,200)
        self.assertTemplateUsed(response,'dle/users/templates/users/register.html') 


    def test_login_users(self):
        user= User.objects.filter(email=self.user['email']).first()
        user.is_active=True
        user.save()
        self.assertEqual(response.status_code,302) 

    def test_login_page(self):
        response = self.login_url
        self.assertEqual(response.status_code,200)
        self.assertTemplateUsed(response,'dle/users/templates/users/login.html')