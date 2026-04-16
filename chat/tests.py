from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status as http_status
from .models import Conversation, DirectMessage

User = get_user_model()


class ConversationModelTests(TestCase):
    """Tests for the Conversation model."""

    def setUp(self):
        self.user1 = User.objects.create_user(
            email='u1@finova.com', username='user1', password='TestPass123!'
        )
        self.user2 = User.objects.create_user(
            email='u2@finova.com', username='user2', password='TestPass123!'
        )

    def test_conversation_creation(self):
        conv = Conversation.objects.create(
            participant_one=self.user1, participant_two=self.user2
        )
        self.assertIsNotNone(conv.id)
        self.assertEqual(conv.participant_one, self.user1)
        self.assertEqual(conv.participant_two, self.user2)

    def test_get_other_participant(self):
        conv = Conversation.objects.create(
            participant_one=self.user1, participant_two=self.user2
        )
        self.assertEqual(conv.get_other_participant(self.user1), self.user2)
        self.assertEqual(conv.get_other_participant(self.user2), self.user1)

    def test_unique_conversation_pair(self):
        Conversation.objects.create(
            participant_one=self.user1, participant_two=self.user2
        )
        # Attempting same pair should raise
        with self.assertRaises(Exception):
            Conversation.objects.create(
                participant_one=self.user1, participant_two=self.user2
            )


class DirectMessageModelTests(TestCase):
    """Tests for the DirectMessage model with auto-parsing."""

    def setUp(self):
        self.user1 = User.objects.create_user(
            email='u1@finova.com', username='user1', password='TestPass123!'
        )
        self.user2 = User.objects.create_user(
            email='u2@finova.com', username='user2', password='TestPass123!'
        )
        self.conv = Conversation.objects.create(
            participant_one=self.user1, participant_two=self.user2
        )

    def test_text_message(self):
        msg = DirectMessage.objects.create(
            conversation=self.conv, sender=self.user1, content='Hello!'
        )
        self.assertEqual(msg.message_type, 'text')
        self.assertIsNone(msg.stock_symbol)

    def test_stock_card_auto_parsed(self):
        msg = DirectMessage.objects.create(
            conversation=self.conv, sender=self.user1,
            content='Check /stocks "AAPL" today',
        )
        self.assertEqual(msg.message_type, 'stock_card')
        self.assertEqual(msg.stock_symbol, 'AAPL')

    def test_read_receipt(self):
        msg = DirectMessage.objects.create(
            conversation=self.conv, sender=self.user1,
            content='Read this'
        )
        self.assertFalse(msg.is_read)
        msg.is_read = True
        msg.save()
        self.assertTrue(msg.is_read)


class ChatAPITests(TestCase):
    """API integration tests for chat endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            email='u1@finova.com', username='user1', password='TestPass123!'
        )
        self.user2 = User.objects.create_user(
            email='u2@finova.com', username='user2', password='TestPass123!'
        )
        self.client.force_authenticate(user=self.user1)

    def test_start_conversation(self):
        response = self.client.post('/api/chat/start/', {
            'finova_id': self.user2.finova_id,
        })
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)
        self.assertTrue(response.data['is_new'])

    def test_start_conversation_duplicate(self):
        """Starting a conversation twice returns the existing one."""
        self.client.post('/api/chat/start/', {'finova_id': self.user2.finova_id})
        response = self.client.post('/api/chat/start/', {
            'finova_id': self.user2.finova_id,
        })
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertFalse(response.data['is_new'])

    def test_start_conversation_with_self(self):
        response = self.client.post('/api/chat/start/', {
            'finova_id': self.user1.finova_id,
        })
        self.assertEqual(response.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_find_user(self):
        response = self.client.get(f'/api/chat/find/{self.user2.finova_id}/')
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertEqual(response.data['finova_id'], self.user2.finova_id)

    def test_list_conversations(self):
        Conversation.objects.create(
            participant_one=self.user1, participant_two=self.user2
        )
        response = self.client.get('/api/chat/')
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)

    def test_send_and_list_messages(self):
        conv = Conversation.objects.create(
            participant_one=self.user1, participant_two=self.user2
        )
        # Send a message
        response = self.client.post(
            f'/api/chat/{conv.id}/messages/',
            {'content': 'Hello from user1!'}
        )
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)

        # List messages
        response = self.client.get(f'/api/chat/{conv.id}/messages/')
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)

    def test_mark_read(self):
        conv = Conversation.objects.create(
            participant_one=self.user1, participant_two=self.user2
        )
        # User2 sends a message
        DirectMessage.objects.create(
            conversation=conv, sender=self.user2, content='Hey there!'
        )
        # User1 marks as read
        response = self.client.post(f'/api/chat/{conv.id}/read/')
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertEqual(response.data['updated_count'], 1)

    def test_find_nonexistent_user(self):
        response = self.client.get('/api/chat/find/ZZZZZZ/')
        self.assertEqual(response.status_code, http_status.HTTP_404_NOT_FOUND)
