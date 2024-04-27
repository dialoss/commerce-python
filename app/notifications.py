import urllib.parse

import requests
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from fcm import token


class Notification:
    def __init__(self, user, type, data):
        self.user = user
        self.type = type
        self.data = data

    def push(self):
        message_token = self.user.messageToken
        if not message_token:
            return
        requests.post("https://fcm.googleapis.com//v1/projects/mymount-d1cad/messages:send", headers={
            'content-type': 'application/json',
            'authorization': 'Bearer ' + token
        }, json={
            "message": {
                "token": message_token,
                "notification": {
                    "title": self.data['title'],
                    "body": self.data['body'],
                    "image": 'https://res.cloudinary.com/drlljn0sj/image/upload/v1712768641/zh13upo4wjh2wbuzarqk.png',
                },
                "webpush": {
                    "fcm_options": {
                        "link": self.data['link'],
                    }
                },
            }})

    def email(self):
        try:
            html_message = render_to_string(self.type + '.html', {'context': self.data})
        except:
            return
        plain_message = strip_tags(html_message)

        send_mail(
            self.data['title'],
            plain_message,
            "maradonner75@gmail.com",
            [self.user.email],
            fail_silently=False,
            html_message=html_message
        )

    def telegram(self):
        TOKEN = "7073660176:AAGxti0mMrUQJoAXLVsxEwi00VhWrzVt3RI"
        chatId = self.user.telegramId
        if not chatId:
            return
        message = f"<b>{self.data['title']}</b>\n{self.data['body']}\n{self.data['link']}"
        payload = {'chat_id': chatId, 'text': message, "parse_mode": 'HTML'}
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?" + urllib.parse.urlencode(payload)
        requests.get(url)
