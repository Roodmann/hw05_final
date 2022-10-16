from http import HTTPStatus

from django.test import TestCase, Client
from ..models import Post, Group, User
from django.urls import reverse


class URLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Name')
        cls.group = Group.objects.create(
            title='Тестовое заголовок',
            description='Тестовое описание',
            slug='test-slug'
        )
        cls.post = Post.objects.create(
            text='b' * 20,
            author=cls.user,
            group=cls.group,
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.URL_INDEX = reverse('posts:home')
        self.URL_GROUP = reverse('posts:group_list',
                                 kwargs={'slug': self.group.slug})
        self.URL_PROFILE = reverse('posts:profile',
                                   kwargs={'username': 'Name'})
        self.URL_POST = reverse('posts:post_detail',
                                kwargs={'post_id': self.post.id})
        self.URL_EDIT = reverse('posts:post_edit',
                                kwargs={'post_id': self.post.id})
        self.URL_CREATE = reverse('posts:create')

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            self.URL_INDEX: 'posts/index.html',
            self.URL_GROUP: 'posts/group_list.html',
            self.URL_PROFILE: 'posts/profile.html',
            self.URL_POST: 'posts/post_detail.html',
            self.URL_EDIT: 'posts/post_create.html',
            self.URL_CREATE: 'posts/post_create.html',
        }

        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_redirect_guest_client(self):
        """Редирект неавторизованного пользователя"""
        url1 = '/auth/login/?next=/create/'
        url2 = f'/auth/login/?next=/posts/{self.post.id}/edit/'
        pages = {'/create/': url1,
                 f'/posts/{self.post.id}/edit/': url2}
        for page, value in pages.items():
            response = self.guest_client.get(page)
            self.assertRedirects(response, value)

    def tes_redirect_anonymous_on_admin_login(self):
        """Редирект анонимного пользователя"""
        response = self.client.get('/posts/test-slug/', follow=True)
        self.assertRedirects(
            response, ('/admin/login/?next=/posts/test-slug/'))

    def test_template_available_authorized_use(self):
        """Шаблон index.html доступен авторизованному пользователю."""
        response = self.authorized_client.get('/')
        self.assertTemplateUsed(response, 'posts/index.html')

    def test_url_to_create_new__page_for_authorized_client(self):
        """Проверка для авторизованного пользователя URL /create/."""
        response = self.authorized_client.get('/create/')
        self.assertTemplateUsed(response, 'posts/post_create.html')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_group_slug(self):
        """Страница /group/test-slug/ доступна любому пользователю."""
        response = self.guest_client.get(f'/group/{self.group.slug}/')
        self.assertEqual(response.status_code, HTTPStatus.OK)
