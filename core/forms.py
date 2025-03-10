from django import forms
from accounts.models import Profile

class ContactForm(forms.Form):
    name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={
        'placeholder': 'Your Name', 'class': 'w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
    }))
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'placeholder': 'Your Email', 'class': 'w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
    }))
    subject = forms.CharField(max_length=200, widget=forms.TextInput(attrs={
        'placeholder': 'Subject', 'class': 'w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
    }))
    message = forms.CharField(widget=forms.Textarea(attrs={
        'placeholder': 'Your Message', 'rows': 5, 'class': 'w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
    }))

class ProfileUpdateForm(forms.ModelForm):
    date_of_birth = forms.DateField(
        required=False, widget=forms.DateInput(attrs={'type': 'date'})
    )
    national_id_number = forms.CharField(
        max_length=50, required=False, widget=forms.TextInput(attrs={'placeholder': 'Enter your National ID'})
    )

    class Meta:
        model = Profile
        fields = ['date_of_birth', 'national_id_number']