import time

import requests
from django.test import TestCase
from tastypie.test import ResourceTestCaseMixin


class PeopleResourceTest(ResourceTestCaseMixin, TestCase):

    def setUp(self):
        super().setUp()
        self.url1 = "http://localhost:8000/api/v1/peoples/?name=abcd"
        self.url2 = "http://localhost:8000/api/v1/peoples/?name=Luke"
        self.rate_limit = 10
        self.throttle_at = 100
        self.headers = {
            'authorization': 'apikey api_client_1:204db7bcfafb2deb7506b89eb3b9b715b09905c8',
        }

    def test_rate_limit(self):
        i = 0
        while i <= self.rate_limit:
            response = requests.get(self.url1, headers=self.headers)
            if i == self.rate_limit:
                self.assertEqual(response.status_code, 429)
            i = i+1

    def test_throttle(self):
        time.sleep(61)
        i = 1
        while i <= self.throttle_at:
            response = requests.get(self.url2, headers=self.headers)
            if i == self.throttle_at:
                self.assertEqual(response.status_code, 429)
            i = i+1
