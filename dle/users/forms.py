from django import forms
from data.models import SOURCES

class MyLabelForm(forms.Form):
    name = forms.CharField(label='Drug Label Name', max_length=255, required=True)
    file = forms.FileField(label='Drug Label File', required=True)
    source = forms.ChoiceField(choices=SOURCES, required=True)
    product_name = forms.CharField(label='Product Name', max_length=255, required=True)
    generic_name = forms.CharField(label='Generic name', max_length=255, required=True)
    product_number = forms.CharField(label='Product Number', max_length=255, required=True)
    marketer = forms.CharField(label='Marketer', max_length=255, required=True)

