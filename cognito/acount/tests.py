from django.test import TestCase
from rest_framework.test import APITestCase
import time
import json
import uuid


class TestSignUpAPIView(APITestCase):

    TARGET_URL = '/api/signup/'

    def test_signup_success(self):
        params = {
            'username': str(uuid.uuid4())[:29],
            'password': "Password56789"
        }
        # APIリクエストを実行
        response = self.client.post(
            self.TARGET_URL,
            params,
            format='json'
        )

        # レスポンスの内容を検証
        self.assertEqual(response.status_code, 201)

        print(response.data)


class TestLoginAPIView(APITestCase):

    TARGET_URL = '/api/login/'

    def test_login_success(self):
        params = {
            'username': str(uuid.uuid4())[:29],
            'password': 'Password56789'
        }
        # ユーザー作成を実行
        response = self.client.post(
            '/api/signup/',
            params,
            format='json'
        )
        time.sleep(5)
        # ログインを実行
        response = self.client.post(
            self.TARGET_URL,
            params,
            format='json'
        )

        # レスポンスの内容を検証
        self.assertEqual(response.status_code, 200)

        # レスポンスの中身を出力
        #print(response.data)


class TestNotLoginRequiredAPIView(APITestCase):

    TARGET_URL = '/api/notlogin/'

    def test_access_success(self):
        # APIを実行
        response = self.client.get(
            self.TARGET_URL,
            format='json'
        )
        self.assertEqual(response.status_code, 200)

        print(response.data)


class TestLoginRequiredAPIView(APITestCase):

    TARGET_URL = '/api/needlogin/'

    def test_access_success(self):
        # APIを実行
        params = {
            'username': str(uuid.uuid4())[:29],
            'password': 'Password56789'
        }
        # ユーザー作成を実行
        response = self.client.post(
            '/api/signup/',
            params,
            format='json'
        )
        time.sleep(5)
        # ログインを実行
        response = self.client.post(
            '/api/login/',
            params,
            format='json'
        )
        res = response.json()
        print(res)
        self.client.credentials(
            HTTP_AUTHORIZATION='Token {}'.format(res['access_token']))

        # APIを実行
        response = self.client.get(
            self.TARGET_URL,
            format='json'
        )
        print(response.data)
        self.assertEqual(response.status_code, 200)
