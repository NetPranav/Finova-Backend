from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status as http_status
from .models import Group, GroupMember, GroupMessage, Discussion, TradePoll, Vote
from .utils import parse_stock_template, detect_message_type

User = get_user_model()


class StockTemplateParserTests(TestCase):
    """Tests for the /stocks template parsing utility."""

    def test_parse_single_stock(self):
        result = parse_stock_template('/stocks "AAPL"')
        self.assertEqual(result, ['AAPL'])

    def test_parse_multiple_stocks(self):
        result = parse_stock_template('Check /stocks "AAPL" and /stocks "TSLA"')
        self.assertEqual(result, ['AAPL', 'TSLA'])

    def test_parse_no_stocks(self):
        result = parse_stock_template('Just a regular message')
        self.assertEqual(result, [])

    def test_parse_case_insensitive(self):
        result = parse_stock_template('/Stocks "reliance"')
        self.assertEqual(result, ['RELIANCE'])

    def test_detect_message_type_stock(self):
        msg_type, symbol = detect_message_type('/stocks "AAPL"')
        self.assertEqual(msg_type, 'stock_card')
        self.assertEqual(symbol, 'AAPL')

    def test_detect_message_type_text(self):
        msg_type, symbol = detect_message_type('Hello everyone!')
        self.assertEqual(msg_type, 'text')
        self.assertIsNone(symbol)


class GroupModelTests(TestCase):
    """Tests for group creation and Finova ID generation."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@finova.com', username='testuser', password='TestPass123!'
        )

    def test_group_creation_generates_finova_id(self):
        group = Group.objects.create(
            name='Test Group', created_by=self.user, max_members=10,
        )
        self.assertIsNotNone(group.finova_id)
        self.assertTrue(group.finova_id.startswith('GRP-'))
        self.assertEqual(len(group.finova_id), 10)  # GRP- + 6 chars

    def test_group_member_count(self):
        group = Group.objects.create(
            name='Test Group', created_by=self.user, max_members=5,
        )
        GroupMember.objects.create(group=group, user=self.user, role='admin')
        self.assertEqual(group.member_count, 1)

    def test_group_is_full(self):
        group = Group.objects.create(
            name='Tiny Group', created_by=self.user, max_members=2,
        )
        user2 = User.objects.create_user(
            email='u2@finova.com', username='user2', password='TestPass123!'
        )
        GroupMember.objects.create(group=group, user=self.user, role='admin')
        GroupMember.objects.create(group=group, user=user2, role='member')
        self.assertTrue(group.is_full)


class GroupMessageAutoParseTests(TestCase):
    """Tests that messages auto-detect /stocks templates."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@finova.com', username='testuser', password='TestPass123!'
        )
        self.group = Group.objects.create(
            name='Test Group', created_by=self.user,
        )

    def test_text_message_stays_text(self):
        msg = GroupMessage.objects.create(
            group=self.group, sender=self.user, content='Hello!'
        )
        self.assertEqual(msg.message_type, 'text')
        self.assertIsNone(msg.stock_symbol)

    def test_stock_template_auto_parsed(self):
        msg = GroupMessage.objects.create(
            group=self.group, sender=self.user,
            content='Check out /stocks "RELIANCE" today',
        )
        self.assertEqual(msg.message_type, 'stock_card')
        self.assertEqual(msg.stock_symbol, 'RELIANCE')


class DiscussionToPollTests(TestCase):
    """Tests for the Discussion → Poll pipeline and Turbo-Reduction."""

    def setUp(self):
        self.users = []
        for i in range(5):
            u = User.objects.create_user(
                email=f'u{i}@finova.com', username=f'user{i}', password='TestPass123!'
            )
            self.users.append(u)

        self.group = Group.objects.create(
            name='Voting Group', created_by=self.users[0], max_members=10,
        )
        for u in self.users:
            GroupMember.objects.create(group=self.group, user=u, role='member')

        self.discussion = Discussion.objects.create(
            group=self.group,
            proposed_by=self.users[0],
            stock_symbol='AAPL',
            stock_name='Apple Inc.',
            discussion_type='buy',
            reasoning='Strong Q4 earnings expected.',
            min_engagement_to_unlock_vote=3,
        )

    def test_discussion_cannot_unlock_early(self):
        self.assertFalse(self.discussion.can_unlock_voting)

    def test_discussion_unlocks_at_threshold(self):
        self.discussion.engagement_count = 3
        self.discussion.save()
        self.assertTrue(self.discussion.can_unlock_voting)

    def test_unlock_creates_poll(self):
        self.discussion.engagement_count = 3
        self.discussion.save()
        poll = self.discussion.unlock_voting()
        self.assertIsNotNone(poll)
        self.assertEqual(self.discussion.status, 'voting')
        self.assertEqual(poll.status, 'active')

    def test_turbo_reduction(self):
        """When all 5 members vote, remaining time should reduce by 90%."""
        self.discussion.engagement_count = 3
        self.discussion.save()
        poll = self.discussion.unlock_voting()

        for i, user in enumerate(self.users):
            Vote.objects.create(poll=poll, voter=user, choice='buy')
            poll.result_buy_count += 1
        poll.save()

        poll.apply_turbo_reduction()
        self.assertTrue(poll.turbo_reduction_applied)
        self.assertIsNotNone(poll.reduced_deadline)


class GroupAPITests(TestCase):
    """API integration tests for group endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='api@finova.com', username='apiuser', password='TestPass123!'
        )
        self.client.force_authenticate(user=self.user)

    def test_create_group(self):
        response = self.client.post('/api/groups/', {
            'name': 'My Investment Club',
            'description': 'A test group',
            'risk_level': 'moderate',
            'max_members': 10,
        })
        self.assertEqual(response.status_code, http_status.HTTP_201_CREATED)
        self.assertIn('finova_id', response.data)

    def test_list_groups(self):
        group = Group.objects.create(name='G1', created_by=self.user)
        GroupMember.objects.create(group=group, user=self.user, role='admin')

        response = self.client.get('/api/groups/')
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)

    def test_join_group(self):
        other_user = User.objects.create_user(
            email='other@finova.com', username='other', password='TestPass123!'
        )
        group = Group.objects.create(name='Open Group', created_by=other_user, max_members=10)
        GroupMember.objects.create(group=group, user=other_user, role='admin')

        response = self.client.post(f'/api/groups/{group.finova_id}/join/')
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
