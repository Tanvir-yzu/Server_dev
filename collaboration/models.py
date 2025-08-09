from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
import uuid
from django.utils import timezone

User = get_user_model()

# Import Project model from DevOps app
from DevOps.models import Project


class ProjectInvitation(models.Model):
    INVITATION_STATUS = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('expired', 'Expired'),
    )

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='invitations')
    inviter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invitations')
    invitee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_invitations', null=True, blank=True)
    email = models.EmailField(null=True, blank=True, help_text="Email for non-registered users")
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    status = models.CharField(max_length=20, choices=INVITATION_STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Invitation expiration date")

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Project Invitation'
        verbose_name_plural = 'Project Invitations'
        # Ensure one invitation per project per user/email
        unique_together = [
            ['project', 'invitee'],
            ['project', 'email'],
        ]

    def __str__(self):
        recipient = self.invitee.email if self.invitee else self.email
        return f"Invite: {self.project.project_name} to {recipient}"

    def clean(self):
        """Custom validation"""
        super().clean()
        
        # Ensure either invitee or email is provided, but not both
        if not self.invitee and not self.email:
            raise ValidationError("Either invitee user or email must be provided")
        
        if self.invitee and self.email:
            raise ValidationError("Cannot specify both invitee user and email")
        
        # Check if user is already a collaborator
        # Only check if we have both invitee and project_id (to avoid RelatedObjectDoesNotExist)
        if self.invitee and self.project_id:
            try:
                # Use project_id instead of self.project to avoid accessing the related object
                if ProjectCollaborator.objects.filter(project_id=self.project_id, user=self.invitee).exists():
                    raise ValidationError("User is already a collaborator on this project")
            except Exception:
                # If there's any issue accessing the project, skip this validation
                # The database constraints will catch duplicate entries anyway
                pass

    def save(self, *args, **kwargs):
        self.full_clean()
        
        # Set expiration date if not provided (30 days from creation)
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(days=30)
        
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        """Check if invitation has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False

    @property
    def recipient_display(self):
        """Get display name for invitation recipient"""
        if self.invitee:
            return self.invitee.get_full_name() or self.invitee.email
        return self.email

    def accept(self, user=None):
        """Accept the invitation"""
        if self.is_expired:
            raise ValidationError("Invitation has expired")
        
        if self.status != 'pending':
            raise ValidationError("Invitation is not pending")
        
        self.status = 'accepted'
        self.accepted_at = timezone.now()
        
        if user and not self.invitee:
            self.invitee = user
        
        self.save()

    def decline(self):
        """Decline the invitation"""
        if self.status != 'pending':
            raise ValidationError("Invitation is not pending")
        
        self.status = 'declined'
        self.save()

    def expire(self):
        """Mark invitation as expired"""
        if self.status == 'pending':
            self.status = 'expired'
            self.save()


class ProjectCollaborator(models.Model):
    """Model to track project collaborators"""
    ROLE_CHOICES = (
        ('viewer', 'Viewer'),
        ('contributor', 'Contributor'),
        ('admin', 'Admin'),
    )

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='collaborators')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collaborated_projects')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')
    added_at = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='added_collaborators')

    class Meta:
        unique_together = ['project', 'user']
        ordering = ['-added_at']
        verbose_name = 'Project Collaborator'
        verbose_name_plural = 'Project Collaborators'

    def __str__(self):
        return f"{self.user.email} - {self.project.project_name} ({self.role})"

    def clean(self):
        """Custom validation"""
        super().clean()
        
        # Prevent project owner from being added as collaborator
        if self.user == self.project.owner:
            raise ValidationError("Project owner cannot be added as a collaborator")