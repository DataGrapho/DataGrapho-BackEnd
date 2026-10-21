from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Usuario
from chatbot.models import ChatSession


class ChatSessionIsolationTest(TestCase):
    """Uma conta nunca deve enxergar ou alterar as sessões de outra conta."""

    def setUp(self):
        self.user_a = Usuario.objects.create_user(
            email='a@teste.com', password='senha-a-123', cpf='111.111.111-11', nome='A'
        )
        self.user_b = Usuario.objects.create_user(
            email='b@teste.com', password='senha-b-123', cpf='222.222.222-22', nome='B'
        )
        self.session_a = ChatSession.objects.create(user=self.user_a, title='Chat da conta A')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user_b)

    def test_list_does_not_include_other_accounts_sessions(self):
        response = self.client.get(reverse('chatbot:sessions-list'))

        self.assertEqual(response.status_code, 200)
        ids = [item['id'] for item in response.json()]
        self.assertNotIn(str(self.session_a.session_id), ids)

    def test_detail_of_other_accounts_session_is_not_found(self):
        url = reverse('chatbot:sessions-detail', args=[self.session_a.session_id])

        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.patch(url, {'title': 'invadido'}, format='json').status_code, 404)
        self.assertEqual(self.client.delete(url).status_code, 404)

        self.session_a.refresh_from_db()
        self.assertEqual(self.session_a.title, 'Chat da conta A')
        self.assertTrue(ChatSession.objects.filter(pk=self.session_a.pk).exists())
