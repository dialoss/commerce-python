import json

import requests
from oauth2client.service_account import ServiceAccountCredentials
import time

scopes = ["https://www.googleapis.com/auth/drive"]

try:
    file = "web/client_secrets.json"
    credentials = ServiceAccountCredentials.from_json_keyfile_name(file, scopes)
except:
    file = "/home/dialoss75/python-commerce/app/web/client_secrets.json"
    credentials = ServiceAccountCredentials.from_json_keyfile_name(file, scopes)

token_url = 'https://oauth2.googleapis.com/token?grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer&assertion='


class GoogleAuthentication:
    token = ''
    time_created = 0.0
    refreshed = False

    @classmethod
    def auth(cls):
        jwt = credentials.create_scoped(scopes)._generate_assertion().decode('utf-8')
        token = json.loads(requests.post(token_url + jwt).content)
        return token['access_token']

    @classmethod
    def get_credentials(cls):
        cls.refreshed = False
        if time.time() - cls.time_created > 3400:
            cls.token = cls.auth()
            cls.time_created = time.time()
            cls.refreshed = True
        return {'token': cls.token, 'refreshed': cls.refreshed}
