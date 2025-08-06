# accounts/views.py
from django.shortcuts import redirect
from django.contrib.auth import logout
from django.views.generic import CreateView, FormView, TemplateView, UpdateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login, authenticate
from django.contrib import messages
from .forms import CustomUserRegistrationForm, CustomAuthenticationForm, ProfileEditForm
from .models import CustomUser, Profile


# -------------------------------
# ✅ RegisterView (Class-Based)
# -------------------------------
class RegisterView(CreateView):
    form_class = CustomUserRegistrationForm
    template_name = 'register.html'
    success_url = reverse_lazy('profile')

    def form_valid(self, form):
        # Save the user
        response = super().form_valid(form)
        user = form.save()  # user is saved with email as username, full_name set

        # Create the profile
        Profile.objects.create(user=user)

        # Auto-login the user
        login(self.request, user)
        return response


# -------------------------------
# ✅ LoginView (Class-Based, using our custom form)
# -------------------------------
class LoginView(FormView):
    form_class = CustomAuthenticationForm
    template_name = 'login.html'
    success_url = reverse_lazy('devops:dashboard')

    def form_valid(self, form):
        email = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        user = authenticate(email=email, password=password)

        if user is not None:
            login(self.request, user)
            return super().form_valid(form)
        else:
            form.add_error(None, "Invalid email or password")
            return self.form_invalid(form)


# -------------------------------
# ✅ LogoutView (Function-Based - accepts GET requests)
# -------------------------------
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('login')


# -------------------------------
# ✅ ProfileView (Class-Based - shows user profile)
# -------------------------------
class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'profile.html'
    login_url = reverse_lazy('login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        profile = user.profile  # Assuming you have a 1-to-1 Profile and it's accessible as .profile
        context['user'] = user
        context['profile'] = profile
        return context


# ✅ EditProfileView (Class-Based - UpdateView)
# -------------------------------
class EditProfileView(LoginRequiredMixin, UpdateView):
    model = Profile
    form_class = ProfileEditForm
    template_name = 'edit_profile.html'
    success_url = reverse_lazy('profile')
    login_url = reverse_lazy('login')

    def get_object(self, queryset=None):
        # Ensure user can only edit their own profile
        profile, created = Profile.objects.get_or_create(user=self.request.user)
        return profile

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        # Update user fields from the form
        user = self.request.user
        user.full_name = form.cleaned_data.get('full_name', user.full_name)
        user.email = form.cleaned_data.get('email', user.email)
        user.save()
        
        # Save the profile
        response = super().form_valid(form)
        messages.success(self.request, 'Profile updated successfully!')
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        context['profile'] = self.object
        return context