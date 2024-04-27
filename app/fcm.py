import json

import requests
from django.core.mail import send_mail
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.views.decorators.csrf import csrf_exempt

from oauth2client.service_account import ServiceAccountCredentials

from web.models import User

SCOPES = ['https://www.googleapis.com/auth/firebase.messaging']

try:
    credential = ServiceAccountCredentials.from_json_keyfile_name(
        './creds.json', SCOPES)
except:
    credential = ServiceAccountCredentials.from_json_keyfile_name(
        '/home/dialoss75/python-commerce/app/creds.json', SCOPES)

token = credential.get_access_token().access_token
