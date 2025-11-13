from django.test import TestCase, Client

class BasicTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_admin_loads(self):
        response = self.client.get('/admin/login/')
        self.assertEqual(response.status_code, 200)

    def test_static_files_config(self):
        from django.conf import settings
        self.assertTrue(hasattr(settings, 'STATIC_ROOT'))
        self.assertTrue(hasattr(settings, 'MEDIA_ROOT'))
