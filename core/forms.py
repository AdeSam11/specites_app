from django import forms

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
