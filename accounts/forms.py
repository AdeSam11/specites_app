from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget

from .models import User


class UserRegistrationForm(UserCreationForm):
    phone_number = forms.CharField(
        max_length=15, 
        widget=forms.TextInput(attrs={'placeholder': 'Enter phone number'})
    )
    country_code = forms.CharField(
        max_length=6,
        required=True,
        widget=forms.TextInput(attrs={'readonly': 'readonly', 'class': 'bg-gray-200'}),
    )
    country = CountryField().formfield(
        max_length=3,
        widget=CountrySelectWidget(attrs={'class': 'form-control'})
    )
    referral_code = forms.CharField(
        max_length=10, required=False, label="Referral Code (Optional)"
    )
    first_name = forms.CharField(widget=forms.TextInput(attrs={'autofocus': 'on'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'autofocus': 'off'}))

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'email',
            'country',
            'country_code',
            'phone_number',
            'password1',
            'password2',
            'city',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': (
                    'appearance-none block w-full bg-gray-200 '
                    'text-gray-700 border border-gray-200 '
                    'rounded py-3 px-4 leading-tight '
                    'focus:outline-none focus:bg-white '
                    'focus:border-gray-500'
                )
            })


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'mt-1 p-2 w-full border rounded-lg focus:outline-none focus:ring focus:ring-indigo-300',
        'placeholder': 'Enter your email'
    }), label="Email")

    def clean(self):
        email = self.cleaned_data.get('username')  # Django still calls this 'username'
        password = self.cleaned_data.get('password')

        if email and password:
            self.user_cache = authenticate(username=email, password=password)
            if self.user_cache is None:
                raise forms.ValidationError("Invalid email or password.")
        
        return self.cleaned_data
    
