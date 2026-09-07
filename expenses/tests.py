from django.contrib.auth import get_user_model
from django.test import TestCase


class MemberModelTests(TestCase):
    def test_member_is_the_project_user_model(self):
        self.assertEqual(get_user_model()._meta.label, 'expenses.Member')

    def test_str_is_the_display_name(self):
        member = get_user_model()(username='alice', name='Alice')
        self.assertEqual(str(member), 'Alice')

    def test_str_falls_back_to_username_when_unnamed(self):
        member = get_user_model()(username='alice')
        self.assertEqual(str(member), 'alice')

    def test_create_superuser(self):
        member = get_user_model().objects.create_superuser(
            username='alice', password='devpassword123'
        )
        self.assertTrue(member.is_superuser)
        self.assertTrue(member.is_staff)
        self.assertTrue(member.check_password('devpassword123'))


class MemberAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.member = get_user_model().objects.create_superuser(
            username='alice', name='Alice', password='devpassword123'
        )

    def setUp(self):
        self.client.force_login(self.member)

    def test_admin_pages_render(self):
        for url in [
            '/admin/',
            '/admin/expenses/member/',
            '/admin/expenses/member/add/',
            f'/admin/expenses/member/{self.member.pk}/change/',
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_add_form_captures_the_display_name(self):
        response = self.client.post(
            '/admin/expenses/member/add/',
            {
                'username': 'bob',
                'name': 'Bob',
                'password1': 'devpassword123',
                'password2': 'devpassword123',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            get_user_model().objects.get(username='bob').name, 'Bob'
        )
