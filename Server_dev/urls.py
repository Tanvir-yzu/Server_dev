
from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('Auth.urls')),
    path('accounts/', include('allauth.urls')),  # Add allauth URLs
    #path('devops/', include('DevOps.urls')),
    path('', include('DevOps.urls')),
    path('collaboration/', include('collaboration.urls')),
    path('system/', include('System.urls')),  # Add System app URLs



]
# serve media files in development environment --------------------------------
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT
    )
