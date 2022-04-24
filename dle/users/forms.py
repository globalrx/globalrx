from django import forms
from data.models import SOURCES

class MyLabelForm(forms.Form):
    name = forms.CharField(label='Drug Label name', max_length=255, required=True)
    file = forms.FileField(label='Drug Label file', required=True)
    source = forms.ChoiceField(choices=SOURCES, required=True)
    product_name = forms.CharField(label='Name of the Product', max_length=255, required=True)
    generic_name = forms.CharField(label='generic name', max_length=255, required=True)
    product_number = forms.CharField(label='Product number', max_length=255, required=True)
    marketer = forms.CharField(label='Marketer', max_length=255, required=True)

