# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser, Profile

# -------------------------------
# ✅ Registration Form
# -------------------------------
class CustomUserRegistrationForm(UserCreationForm):
    full_name = forms.CharField(label="Full Name", max_length=255, required=True)
    email = forms.EmailField(label="Email", required=True)

    class Meta:
        model = CustomUser
        fields = ('full_name', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already in use.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.full_name = self.cleaned_data['full_name']
        # Username will be auto-generated in the model's save method
        if commit:
            user.save()
        return user


# -------------------------------
# ✅ Login Form (Email instead of username)
# -------------------------------
class CustomAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={'placeholder': 'Enter your email'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password'].widget.attrs.update({'placeholder': 'Enter your password'})


# -------------------------------
# ✅ Profile Edit Form
# -------------------------------
class ProfileEditForm(forms.ModelForm):
    full_name = forms.CharField(
        label="Full Name", 
        max_length=255, 
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter your full name',
            'class': 'w-full px-4 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-indigo-400'
        })
    )
    email = forms.EmailField(
        label="Email", 
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter your email address',
            'class': 'w-full px-4 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-indigo-400'
        })
    )

    class Meta:
        model = Profile
        fields = ['photo', 'bio', 'github_link']
        widgets = {
            'bio': forms.Textarea(attrs={
                'rows': 4, 
                'placeholder': 'Tell us about yourself...',
                'class': 'w-full px-4 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-indigo-400'
            }),
            'github_link': forms.URLInput(attrs={
                'placeholder': 'https://github.com/yourusername',
                'class': 'w-full px-4 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-indigo-400'
            }),
            'photo': forms.FileInput(attrs={
                'class': 'mt-4 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:border file:border-gray-200 file:rounded file:text-sm file:bg-white file:text-gray-700 hover:file:bg-gray-100',
                'accept': 'image/*'
            })
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['full_name'].initial = self.user.full_name
            self.fields['email'].initial = self.user.email

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if self.user and CustomUser.objects.filter(email=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("This email is already in use.")
        return email

    def clean_github_link(self):
        github_link = self.cleaned_data.get('github_link')
        if github_link and not github_link.startswith('https://github.com/'):
            raise forms.ValidationError("Please enter a valid GitHub URL (https://github.com/username)")
        return github_link

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if photo:
            if photo.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Photo size must be less than 5MB")
            
            from django.core.files.uploadedfile import UploadedFile
            if isinstance(photo, UploadedFile):
                if not photo.content_type.startswith('image/'):
                    raise forms.ValidationError("Please upload a valid image file")
        return photo