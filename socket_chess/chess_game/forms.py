from django import forms
from django.contrib.auth.models import User
from .models import TheGame

class JoinForm(forms.ModelForm):

    password = forms.CharField(widget=forms.PasswordInput(attrs={'autocomplete':'new-password'}))

    email = forms.CharField(widget=forms.TextInput(attrs={'size':'30'}))

    class Meta: 
        model = User
        fields = ['username','first_name','last_name', 'email','password']
    
class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput())

class JournalForm(forms.ModelForm):
    journal = forms.CharField(widget=forms.Textarea(attrs={
        'class': 'form-control',
        'rows': 4,
        'placeholder': 'Write your journal here...'
        }), label='Journal Entry', required=False)

    class Meta: 
        model = TheGame
        fields = ['journal']
    
    def clean_journal(self):
        journal = self.cleaned_data.get('journal','').strip()
        return journal

