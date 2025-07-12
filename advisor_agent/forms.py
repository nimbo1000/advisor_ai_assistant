# hubspot_integration/forms.py
from django import forms

class ContactForm(forms.Form):
    firstname = forms.CharField(max_length=100, required=True)
    lastname = forms.CharField(max_length=100, required=True)
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=False)
    company = forms.CharField(max_length=100, required=False)
    website = forms.URLField(required=False)
    
class NoteForm(forms.Form):
    content = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5}),
        required=True,
        label="Note Content"
    )