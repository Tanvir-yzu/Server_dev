from django.core.management.base import BaseCommand
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site

class Command(BaseCommand):
    help = 'Create social apps for Google and GitHub'

    def handle(self, *args, **options):
        # Get the current site
        try:
            site = Site.objects.get_current()
        except Site.DoesNotExist:
            site = Site.objects.create(name='localhost', domain='localhost:8000')

        # Create Google SocialApp
        google_app, created = SocialApp.objects.get_or_create(
            provider='google',
            defaults={
                'name': 'Google',
                'client_id': 'dummy_google_client_id',  # Replace with real client_id
                'secret': 'dummy_google_secret',  # Replace with real secret
            }
        )
        if created:
            google_app.sites.add(site)
            self.stdout.write(self.style.SUCCESS('Created Google SocialApp'))
        else:
            self.stdout.write('Google SocialApp already exists')

        # Create GitHub SocialApp
        github_app, created = SocialApp.objects.get_or_create(
            provider='github',
            defaults={
                'name': 'GitHub',
                'client_id': 'dummy_github_client_id',  # Replace with real client_id
                'secret': 'dummy_github_secret',  # Replace with real secret
            }
        )
        if created:
            github_app.sites.add(site)
            self.stdout.write(self.style.SUCCESS('Created GitHub SocialApp'))
        else:
            self.stdout.write('GitHub SocialApp already exists')