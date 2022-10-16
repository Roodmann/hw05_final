import shutil
import tempfile

from django import forms
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.core.cache import cache
from django.urls import reverse
from ..models import Follow, Post, Group, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(
            username='Name',
        )
        cls.group = Group.objects.create(
            title='Тестовое название группы',
            slug='test_slug',
            description='Тестовое описание группы',
        )
        post_list = [Post(text=f'Тестовый пост №{i}',
                     group=cls.group, author=cls.user)
                     for i in range(13)]
        Post.objects.bulk_create(post_list)

    def setUp(self):
        self.unauthorized_client = Client()

    def test_paginator_on_pages(self):
        """Проверка пагинации на страницах."""
        posts_on_first_page = 10
        posts_on_second_page = 3
        url_pages = [
            reverse('posts:home'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': 'Name'}),
        ]
        for rev in url_pages:
            with self.subTest(rev=rev):
                response = self.client.get(rev,
                                           {'page': 1})
                self.assertEqual(len(response.context['page_obj']),
                                 posts_on_first_page)

                response = self.client.get(rev,
                                           {'page': 2})
                self.assertEqual(len(response.context['page_obj']),
                                 posts_on_second_page)


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Name')
        cls.group = Group.objects.create(
            title='Тестовое заголовок',
            slug='test-slug',
            description='Тестовое описание',
        )

        cls.post = Post.objects.create(
            text='Текст',
            author=cls.user,
            group=cls.group,
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def post_ifo_massage(self, context):
        with self.subTest(context=context):
            self.assertEqual(context.text, self.post.text)
            self.assertEqual(context.pub_date, self.post.pub_date)
            self.assertEqual(context.author, self.post.author)
            self.assertEqual(context.group.id, self.post.group.id)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            reverse(
                'posts:home'): 'posts/index.html',
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}): 'posts/group_list.html',
            reverse(
                'posts:profile',
                kwargs={'username': 'Name'}): 'posts/profile.html',
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}): 'posts/post_detail.html',
            reverse(
                'posts:post_edit',
                kwargs={'post_id': self.post.id}): 'posts/post_create.html',
            reverse(
                'posts:create'): 'posts/post_create.html',
        }
        for adress, template in templates_url_names.items():
            with self.subTest(adress=adress):
                response = self.authorized_client.get(adress)
                self.assertTemplateUsed(response, template)

    def test_home_page_show_correct_context(self):
        """Шаблон home.html сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:home'))
        self.post_ifo_massage(response.context['page_obj'][0])

    def test_group_page_show_correct_context(self):
        """Шаблон group_list.html сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug})
        )
        self.assertEqual(response.context['group'], self.group)
        self.post_ifo_massage(response.context['page_obj'][0])

    def test_profile_page_show_correct_context(self):
        """Шаблон profile.html сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:profile',
                kwargs={'username': 'Name'}))
        self.assertEqual(response.context['author'], self.user)
        self.post_ifo_massage(response.context['page_obj'][0])

    def test_detail_page_show_correct_context(self):
        """Шаблон post_detail.html сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}))
        self.post_ifo_massage(response.context['post'])


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Name1')
        cls.user2 = User.objects.create_user(username='Name2')

    def setUp(self):
        self.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        self.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=self.small_gif,
            content_type='image/gif'
        )
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.group = Group.objects.create(title='Тестовая группа',
                                          slug='test_group')
        self.post = Post.objects.create(text='Тестовый текст',
                                        group=self.group,
                                        author=self.user,
                                        image=self.uploaded)

    def correct_context_for_pages(self, context):
        """Проверка контекста для главной страницы, групп и профайла."""
        post_object_fields = {
            context.text: self.post.text,
            context.author: self.user,
            context.group: self.group,
            context.group.id: self.group.id,
            context.image: self.post.image,
        }
        for item, expected in post_object_fields.items():
            with self.subTest(item=item):
                self.assertEqual(item, expected)

    def assert_post_response(self, response):
        """Проверяем context форм"""
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.ImageField,
        }

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_cache_index_page(self):
        """Проверка кеша"""
        post = Post.objects.create(
            text='Пост попугая Кеши',
            author=self.user)
        content_add = self.authorized_client.get(
            reverse('posts:home')).content
        post.delete()
        content_delete = self.authorized_client.get(
            reverse('posts:home')).content
        self.assertEqual(content_add, content_delete)
        cache.clear()
        content_cache_clear = self.authorized_client.get(
            reverse('posts:home')).content
        self.assertNotEqual(content_add, content_cache_clear)


class FollowViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Name')
        cls.user2 = User.objects.create_user(username='Name2')
        cls.author = User.objects.create_user(username='somename')

    def setUp(self):
        self.guest_client = Client()
        self.unauthorized_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_client2 = Client()
        self.authorized_client2.force_login(self.user2)

    def test_follow_another_user(self):
        """Авторизованный пользователь,
        может подписываться на других пользователей"""
        follow_count = Follow.objects.count()
        self.authorized_client.get(reverse('posts:profile_follow',
                                           kwargs={'username': self.user2}))
        self.assertTrue(Follow.objects.filter(user=self.user,
                                              author=self.user2).exists())
        self.assertEqual(Follow.objects.count(), follow_count + 1)

    def test_follower_see_new_post(self):
        """Новая запись появляется появляется в ленте подписчика.
           А у не подписчика его нет"""
        new_post_follower = Post.objects.create(
            author=FollowViewsTest.author,
            text='Текстовый текст')
        Follow.objects.create(user=FollowViewsTest.user,
                              author=FollowViewsTest.author)
        response_follower = self.authorized_client.get(
            reverse('posts:home'))
        new_posts = response_follower.context['page_obj']
        self.assertIn(new_post_follower, new_posts)

    def test_follow_unauthor(self):
        """Не авторизованный пользователь,
        может подписываться на других пользователей"""
        follow_count = Follow.objects.count()
        self.unauthorized_client.get(reverse('posts:profile_follow',
                                             kwargs={'username': self.user}))
        self.assertFalse(Follow.objects.filter(user=self.user,
                                               author=self.user).exists())
        self.assertEqual(Follow.objects.count(), follow_count)
