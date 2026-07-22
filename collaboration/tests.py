from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import ProjectInvitation, ProjectCollaborator
from DevOps.models import Project

User = get_user_model()


class ProjectInvitationModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            full_name='Test User',
            password='testpass123!'
        )
        self.project = Project.objects.create(
            project_name='Test Project',
            github_username='testuser',
            database_name='testdb',
            domain_name='test.com',
            project_github_link='https://github.com/testuser/testrepo',
            project_details='Test project details',
            owner=self.user
        )

    def test_invitation_creation_with_user(self):
        """Test invitation creation with existing user"""
        invitee = User.objects.create_user(
            email='invitee@example.com',
            full_name='Invitee User',
            password='testpass123!'
        )
        
        invitation = ProjectInvitation.objects.create(
            project=self.project,
            inviter=self.user,
            invitee=invitee
        )
        
        self.assertEqual(invitation.project, self.project)
        self.assertEqual(invitation.inviter, self.user)
        self.assertEqual(invitation.invitee, invitee)
        self.assertEqual(invitation.status, 'pending')
        self.assertTrue(invitation.token)
        self.assertTrue(invitation.expires_at)

    def test_invitation_creation_with_email(self):
        """Test invitation creation with email (non-registered user)"""
        invitation = ProjectInvitation.objects.create(
            project=self.project,
            inviter=self.user,
            email='newuser@example.com'
        )
        
        self.assertEqual(invitation.project, self.project)
        self.assertEqual(invitation.inviter, self.user)
        self.assertEqual(invitation.email, 'newuser@example.com')
        self.assertIsNone(invitation.invitee)
        self.assertEqual(invitation.status, 'pending')

    def test_invitation_status_choices(self):
        """Test that all invitation status choices are valid"""
        statuses = [choice[0] for choice in ProjectInvitation.INVITATION_STATUS]
        self.assertIn('pending', statuses)
        self.assertIn('accepted', statuses)
        self.assertIn('declined', statuses)
        self.assertIn('cancelled', statuses)
        self.assertIn('expired', statuses)

    def test_invitation_clean_both_fields(self):
        """Test that invitation cannot have both invitee and email"""
        invitee = User.objects.create_user(
            email='invitee@example.com',
            full_name='Invitee User',
            password='testpass123!'
        )
        
        invitation = ProjectInvitation(
            project=self.project,
            inviter=self.user,
            invitee=invitee,
            email='another@example.com'
        )
        
        with self.assertRaises(Exception):
            invitation.full_clean()

    def test_invitation_clean_no_fields(self):
        """Test that invitation must have either invitee or email"""
        invitation = ProjectInvitation(
            project=self.project,
            inviter=self.user
        )
        
        with self.assertRaises(Exception):
            invitation.full_clean()

    def test_invitation_is_expired(self):
        """Test is_expired property"""
        invitation = ProjectInvitation.objects.create(
            project=self.project,
            inviter=self.user,
            email='test@example.com',
            expires_at=timezone.now() - timezone.timedelta(days=1)
        )
        
        self.assertTrue(invitation.is_expired)

    def test_invitation_not_expired(self):
        """Test is_expired property for non-expired invitations"""
        invitation = ProjectInvitation.objects.create(
            project=self.project,
            inviter=self.user,
            email='test@example.com',
            expires_at=timezone.now() + timezone.timedelta(days=1)
        )
        
        self.assertFalse(invitation.is_expired)

    def test_invitation_accept(self):
        """Test invitation accept method"""
        invitation = ProjectInvitation.objects.create(
            project=self.project,
            inviter=self.user,
            email='test@example.com'
        )
        
        invitation.accept(user=self.user)
        
        self.assertEqual(invitation.status, 'accepted')
        self.assertEqual(invitation.invitee, self.user)
        self.assertTrue(invitation.accepted_at)

    def test_invitation_decline(self):
        """Test invitation decline method"""
        invitation = ProjectInvitation.objects.create(
            project=self.project,
            inviter=self.user,
            email='test@example.com'
        )
        
        invitation.decline()
        
        self.assertEqual(invitation.status, 'declined')

    def test_invitation_expire(self):
        """Test invitation expire method"""
        invitation = ProjectInvitation.objects.create(
            project=self.project,
            inviter=self.user,
            email='test@example.com'
        )
        
        invitation.expire()
        
        self.assertEqual(invitation.status, 'expired')


class ProjectCollaboratorModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            full_name='Test User',
            password='testpass123!'
        )
        self.project = Project.objects.create(
            project_name='Test Project',
            github_username='testuser',
            database_name='testdb',
            domain_name='test.com',
            project_github_link='https://github.com/testuser/testrepo',
            project_details='Test project details',
            owner=self.user
        )

    def test_collaborator_creation(self):
        """Test collaborator creation"""
        collaborator_user = User.objects.create_user(
            email='collaborator@example.com',
            full_name='Collaborator User',
            password='testpass123!'
        )
        
        collaborator = ProjectCollaborator.objects.create(
            project=self.project,
            user=collaborator_user,
            role='viewer',
            added_by=self.user
        )
        
        self.assertEqual(collaborator.project, self.project)
        self.assertEqual(collaborator.user, collaborator_user)
        self.assertEqual(collaborator.role, 'viewer')
        self.assertEqual(collaborator.added_by, self.user)

    def test_collaborator_role_choices(self):
        """Test that all collaborator role choices are valid"""
        roles = [choice[0] for choice in ProjectCollaborator.ROLE_CHOICES]
        self.assertIn('viewer', roles)
        self.assertIn('contributor', roles)
        self.assertIn('admin', roles)

    def test_collaborator_unique_together(self):
        """Test that user can't be added as collaborator twice"""
        collaborator_user = User.objects.create_user(
            email='collaborator@example.com',
            full_name='Collaborator User',
            password='testpass123!'
        )
        
        ProjectCollaborator.objects.create(
            project=self.project,
            user=collaborator_user,
            role='viewer',
            added_by=self.user
        )
        
        with self.assertRaises(Exception):
            ProjectCollaborator.objects.create(
                project=self.project,
                user=collaborator_user,
                role='contributor',
                added_by=self.user
            )

    def test_collaborator_clean_owner(self):
        """Test that owner can't be added as collaborator"""
        collaborator = ProjectCollaborator(
            project=self.project,
            user=self.user,
            role='admin',
            added_by=self.user
        )
        
        with self.assertRaises(Exception):
            collaborator.full_clean()


class InvitationAcceptTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='owner@example.com',
            full_name='Owner User',
            password='testpass123!'
        )
        self.invitee = User.objects.create_user(
            email='invitee@example.com',
            full_name='Invitee User',
            password='testpass123!'
        )
        self.other_user = User.objects.create_user(
            email='other@example.com',
            full_name='Other User',
            password='testpass123!'
        )
        self.project = Project.objects.create(
            project_name='Test Project',
            github_username='testuser',
            database_name='testdb',
            domain_name='test.com',
            project_github_link='https://github.com/testuser/testrepo',
            project_details='Test project details',
            owner=self.owner
        )
        self.invitation = ProjectInvitation.objects.create(
            project=self.project,
            inviter=self.owner,
            invitee=self.invitee
        )

    def test_accept_invitation_valid_user(self):
        """Test that valid user can accept invitation"""
        self.client.login(email='invitee@example.com', password='testpass123!')
        url = reverse('collaboration:accept_invitation', kwargs={'token': self.invitation.token})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 302)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.status, 'accepted')
        self.assertTrue(ProjectCollaborator.objects.filter(
            project=self.project,
            user=self.invitee
        ).exists())

    def test_accept_invitation_wrong_user(self):
        """Test that wrong user cannot accept invitation"""
        self.client.login(email='other@example.com', password='testpass123!')
        url = reverse('collaboration:accept_invitation', kwargs={'token': self.invitation.token})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 302)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.status, 'pending')
        self.assertFalse(ProjectCollaborator.objects.filter(
            project=self.project,
            user=self.other_user
        ).exists())

    def test_accept_invitation_already_accepted(self):
        """Test that already accepted invitation cannot be accepted again"""
        self.invitation.status = 'accepted'
        self.invitation.save()
        
        self.client.login(email='invitee@example.com', password='testpass123!')
        url = reverse('collaboration:accept_invitation', kwargs={'token': self.invitation.token})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 302)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.status, 'accepted')

    def test_accept_invitation_expired(self):
        """Test that expired invitation cannot be accepted"""
        self.invitation.expires_at = timezone.now() - timezone.timedelta(days=1)
        self.invitation.save()
        
        self.client.login(email='invitee@example.com', password='testpass123!')
        url = reverse('collaboration:accept_invitation', kwargs={'token': self.invitation.token})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 302)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.status, 'pending')


class InvitationDeclineTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='owner@example.com',
            full_name='Owner User',
            password='testpass123!'
        )
        self.invitee = User.objects.create_user(
            email='invitee@example.com',
            full_name='Invitee User',
            password='testpass123!'
        )
        self.other_user = User.objects.create_user(
            email='other@example.com',
            full_name='Other User',
            password='testpass123!'
        )
        self.project = Project.objects.create(
            project_name='Test Project',
            github_username='testuser',
            database_name='testdb',
            domain_name='test.com',
            project_github_link='https://github.com/testuser/testrepo',
            project_details='Test project details',
            owner=self.owner
        )
        self.invitation = ProjectInvitation.objects.create(
            project=self.project,
            inviter=self.owner,
            invitee=self.invitee
        )

    def test_decline_invitation_valid_user(self):
        """Test that valid user can decline invitation"""
        self.client.login(email='invitee@example.com', password='testpass123!')
        url = reverse('collaboration:decline_invitation', kwargs={'token': self.invitation.token})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 302)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.status, 'declined')

    def test_decline_invitation_wrong_user(self):
        """Test that wrong user cannot decline invitation"""
        self.client.login(email='other@example.com', password='testpass123!')
        url = reverse('collaboration:decline_invitation', kwargs={'token': self.invitation.token})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 302)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.status, 'pending')


class CollaboratorRoleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            full_name='Test User',
            password='testpass123!'
        )
        self.project = Project.objects.create(
            project_name='Test Project',
            github_username='testuser',
            database_name='testdb',
            domain_name='test.com',
            project_github_link='https://github.com/testuser/testrepo',
            project_details='Test project details',
            owner=self.user
        )

    def test_valid_collaborator_roles(self):
        """Test that only valid roles are accepted"""
        valid_roles = ['viewer', 'contributor', 'admin']
        for role in valid_roles:
            other_user = User.objects.create_user(
                email=f'{role}@example.com',
                full_name=f'{role.capitalize()} User',
                password='testpass123!'
            )
            collaborator = ProjectCollaborator.objects.create(
                project=self.project,
                user=other_user,
                role=role,
                added_by=self.user
            )
            self.assertEqual(collaborator.role, role)


class UserSearchTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            full_name='Test User',
            password='testpass123!'
        )
        self.other_user = User.objects.create_user(
            email='other@example.com',
            full_name='Other User Full Name',
            password='testpass123!'
        )
        self.client.login(email='test@example.com', password='testpass123!')

    def test_user_search_by_full_name(self):
        """Test that user search works with full_name field"""
        url = reverse('collaboration:search_users_ajax')
        response = self.client.get(url, {'q': 'Other User'})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['users']), 1)
        self.assertEqual(data['users'][0]['email'], 'other@example.com')

    def test_user_search_by_email(self):
        """Test that user search works with email field"""
        url = reverse('collaboration:search_users_ajax')
        response = self.client.get(url, {'q': 'other@example'})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['users']), 1)
        self.assertEqual(data['users'][0]['email'], 'other@example.com')


class CollaboratorRoleUpdateTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='owner@example.com',
            full_name='Owner User',
            password='testpass123!'
        )
        self.collaborator_user = User.objects.create_user(
            email='collaborator@example.com',
            full_name='Collaborator User',
            password='testpass123!'
        )
        self.project = Project.objects.create(
            project_name='Test Project',
            github_username='testuser',
            database_name='testdb',
            domain_name='test.com',
            project_github_link='https://github.com/testuser/testrepo',
            project_details='Test project details',
            owner=self.owner
        )
        self.collaborator = ProjectCollaborator.objects.create(
            project=self.project,
            user=self.collaborator_user,
            role='viewer',
            added_by=self.owner
        )
        self.client.login(email='owner@example.com', password='testpass123!')

    def test_update_role_via_ajax_json(self):
        """Test that role can be updated via AJAX with JSON payload"""
        url = reverse('collaboration:update_collaborator_role_ajax', kwargs={'collaborator_id': self.collaborator.id})
        response = self.client.post(
            url,
            '{"role": "admin"}',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['new_role'], 'admin')
        
        self.collaborator.refresh_from_db()
        self.assertEqual(self.collaborator.role, 'admin')

    def test_update_role_via_ajax_form_encoded(self):
        """Test that role can be updated via AJAX with form-encoded data"""
        url = reverse('collaboration:update_collaborator_role_ajax', kwargs={'collaborator_id': self.collaborator.id})
        response = self.client.post(
            url,
            {'role': 'contributor'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['new_role'], 'contributor')
        
        self.collaborator.refresh_from_db()
        self.assertEqual(self.collaborator.role, 'contributor')

    def test_update_role_invalid_role(self):
        """Test that invalid role is rejected"""
        url = reverse('collaboration:update_collaborator_role_ajax', kwargs={'collaborator_id': self.collaborator.id})
        response = self.client.post(
            url,
            '{"role": "invalid"}',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Invalid role')

    def test_update_role_permission_denied(self):
        """Test that non-owner/admin cannot update roles"""
        self.client.logout()
        self.client.login(email='collaborator@example.com', password='testpass123!')
        
        url = reverse('collaboration:update_collaborator_role_ajax', kwargs={'collaborator_id': self.collaborator.id})
        response = self.client.post(
            url,
            '{"role": "admin"}',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertEqual(data['error'], 'Permission denied')


class ProjectInvitationDuplicateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            full_name='Test User',
            password='testpass123!'
        )
        self.project = Project.objects.create(
            project_name='Test Project',
            github_username='testuser',
            database_name='testdb',
            domain_name='test.com',
            project_github_link='https://github.com/testuser/testrepo',
            project_details='Test project details',
            owner=self.user
        )

    def test_duplicate_invitation_prevention(self):
        """Test that duplicate invitations are prevented"""
        ProjectInvitation.objects.create(
            project=self.project,
            inviter=self.user,
            email='invitee@example.com'
        )
        
        with self.assertRaises(Exception):
            ProjectInvitation.objects.create(
                project=self.project,
                inviter=self.user,
                email='invitee@example.com'
            )