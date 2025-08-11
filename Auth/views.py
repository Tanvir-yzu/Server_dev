# accounts/views.py
import logging
import time
from functools import wraps
from django.shortcuts import redirect
from django.contrib.auth import logout
from django.views.generic import CreateView, FormView, TemplateView, UpdateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login, authenticate
from django.contrib import messages
from .forms import CustomUserRegistrationForm, CustomAuthenticationForm, ProfileEditForm
from .models import CustomUser, Profile

# Initialize logger for Auth app
logger = logging.getLogger('auth')

def log_auth_action(action_name):
    """
    Decorator to log authentication-related actions with timing and context
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            request = None
            
            # Extract request object from args
            if args and hasattr(args[0], 'request'):
                request = args[0].request
            elif args and hasattr(args[0], 'method'):
                request = args[0]
            
            user_info = "Anonymous"
            if request and hasattr(request, 'user') and request.user.is_authenticated:
                user_info = f"{request.user.email} (ID: {request.user.id})"
            
            logger.info(f"Starting {action_name} - User: {user_info}")
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(f"Completed {action_name} - User: {user_info} - Time: {execution_time:.2f}s")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Failed {action_name} - User: {user_info} - Error: {str(e)} - Time: {execution_time:.2f}s")
                raise
        return wrapper
    return decorator


# -------------------------------
# ✅ RegisterView (Class-Based)
# -------------------------------
class RegisterView(CreateView):
    form_class = CustomUserRegistrationForm
    template_name = 'register.html'
    success_url = reverse_lazy('profile')

    def dispatch(self, request, *args, **kwargs):
        logger.debug(f"RegisterView accessed from IP: {request.META.get('REMOTE_ADDR', 'Unknown')}")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        logger.info("Registration form requested")
        return super().get(request, *args, **kwargs)

    @log_auth_action("User Registration")
    def form_valid(self, form):
        logger.info("Processing valid registration form")
        
        try:
            # Save the user
            response = super().form_valid(form)
            user = form.save()  # user is saved with email as username, full_name set
            
            logger.info(f"New user created: {user.email} (ID: {user.id})")

            # Create the profile
            profile = Profile.objects.create(user=user)
            logger.debug(f"Profile created for user {user.email} (Profile ID: {profile.id})")

            # Auto-login the user
            login(self.request, user)
            logger.info(f"User {user.email} automatically logged in after registration")
            
            return response
            
        except Exception as e:
            logger.error(f"Error during user registration: {str(e)}")
            raise

    def form_invalid(self, form):
        logger.warning(f"Invalid registration form submitted - Errors: {form.errors}")
        return super().form_invalid(form)


# -------------------------------
# ✅ LoginView (Class-Based, using our custom form)
# -------------------------------
class LoginView(FormView):
    form_class = CustomAuthenticationForm
    template_name = 'login.html'
    success_url = reverse_lazy('devops:dashboard')

    def dispatch(self, request, *args, **kwargs):
        logger.debug(f"LoginView accessed from IP: {request.META.get('REMOTE_ADDR', 'Unknown')}")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        logger.info("Login form requested")
        return super().get(request, *args, **kwargs)

    @log_auth_action("User Login")
    def form_valid(self, form):
        email = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        
        logger.debug(f"Login attempt for email: {email}")
        
        user = authenticate(email=email, password=password)

        if user is not None:
            login(self.request, user)
            logger.info(f"Successful login for user: {user.email} (ID: {user.id})")
            
            # Log additional user info
            logger.debug(f"User {user.email} - Last login: {user.last_login}, Active: {user.is_active}")
            
            return super().form_valid(form)
        else:
            logger.warning(f"Failed login attempt for email: {email}")
            form.add_error(None, "Invalid email or password")
            return self.form_invalid(form)

    def form_invalid(self, form):
        email = form.cleaned_data.get('username', 'Unknown') if form.cleaned_data else 'Unknown'
        logger.warning(f"Invalid login form for email: {email} - Errors: {form.errors}")
        return super().form_invalid(form)


# -------------------------------
# ✅ LogoutView (Function-Based - accepts GET requests)
# -------------------------------
@log_auth_action("User Logout")
def logout_view(request):
    user_email = request.user.email if request.user.is_authenticated else "Anonymous"
    user_id = request.user.id if request.user.is_authenticated else None
    
    logger.info(f"Logout requested by user: {user_email} (ID: {user_id})")
    
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    
    logger.info(f"User {user_email} successfully logged out")
    
    return redirect('login')


# -------------------------------
# ✅ ProfileView (Class-Based - shows user profile)
# -------------------------------
class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'profile.html'
    login_url = reverse_lazy('login')

    def dispatch(self, request, *args, **kwargs):
        logger.debug(f"ProfileView accessed by user: {request.user.email if request.user.is_authenticated else 'Anonymous'}")
        return super().dispatch(request, *args, **kwargs)

    @log_auth_action("Profile View")
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        logger.debug(f"Loading profile data for user: {user.email} (ID: {user.id})")
        
        try:
            profile, created = Profile.objects.get_or_create(user=user)
            
            if created:
                logger.info(f"New profile created for existing user: {user.email}")
            else:
                logger.debug(f"Existing profile loaded for user: {user.email}")
            
            context['user'] = user
            context['profile'] = profile
            
            return context
            
        except Exception as e:
            logger.error(f"Error loading profile for user {user.email}: {str(e)}")
            raise


# ✅ EditProfileView (Class-Based - UpdateView)
# -------------------------------
class EditProfileView(LoginRequiredMixin, UpdateView):
    model = Profile
    form_class = ProfileEditForm
    template_name = 'edit_profile.html'
    success_url = reverse_lazy('profile')
    login_url = reverse_lazy('login')

    def dispatch(self, request, *args, **kwargs):
        logger.debug(f"EditProfileView accessed by user: {request.user.email if request.user.is_authenticated else 'Anonymous'}")
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        # Ensure user can only edit their own profile
        user = self.request.user
        logger.debug(f"Getting profile object for user: {user.email}")
        
        try:
            profile, created = Profile.objects.get_or_create(user=user)
            
            if created:
                logger.info(f"New profile created during edit for user: {user.email}")
            
            return profile
            
        except Exception as e:
            logger.error(f"Error getting profile object for user {user.email}: {str(e)}")
            raise

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        logger.debug(f"Form kwargs prepared for user: {self.request.user.email}")
        return kwargs

    @log_auth_action("Profile Update")
    def form_valid(self, form):
        user = self.request.user
        old_email = user.email
        old_full_name = user.full_name
        
        logger.info(f"Processing profile update for user: {user.email}")
        
        try:
            # Update user fields from the form
            new_full_name = form.cleaned_data.get('full_name', user.full_name)
            new_email = form.cleaned_data.get('email', user.email)
            
            # Log changes
            if old_email != new_email:
                logger.info(f"Email change for user {user.id}: {old_email} -> {new_email}")
            if old_full_name != new_full_name:
                logger.info(f"Full name change for user {user.email}: {old_full_name} -> {new_full_name}")
            
            user.full_name = new_full_name
            user.email = new_email
            user.save()
            
            logger.debug(f"User model updated for: {user.email}")
            
            # Save the profile
            response = super().form_valid(form)
            
            logger.info(f"Profile successfully updated for user: {user.email}")
            messages.success(self.request, 'Profile updated successfully!')
            
            return response
            
        except Exception as e:
            logger.error(f"Error updating profile for user {user.email}: {str(e)}")
            raise

    def form_invalid(self, form):
        user = self.request.user
        logger.warning(f"Invalid profile form for user {user.email} - Errors: {form.errors}")
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        context['profile'] = self.object
        
        logger.debug(f"Context data prepared for profile edit: {self.request.user.email}")
        
        return context