from rest_framework import permissions
from rest_framework.permissions import BasePermission, SAFE_METHODS

from jose import jwt

import jose.jwt
from rest_framework.throttling import SimpleRateThrottle

from web.models import User

try:
    secret = open("web/secret", 'r').read()
except:
    secret = open("/home/dialoss75/python-commerce/app/web/secret", 'r').read()


def get_user(headers):
    token = headers.get('Authorization')
    user = headers.get('User')
    if not token or not user:
        return {}, ''
    return jose.jwt.decode(token, secret), user


def check_token(headers, admin=True):
    data, user = get_user(headers)
    if admin:
        u = User.objects.get(userId=data['userId'])
        return data['userUuid'] == user and u.email == 'matthewwimsten@gmail.com'
    return data['userUuid'] == user


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        return request.method in permissions.SAFE_METHODS


class CreateOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in ('POST')

    def has_object_permission(self, request, view, obj):
        return request.method in ('POST')


class AdminPermission(BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        return check_token(request.headers)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        return check_token(request.headers)


class OwnerPermission(BasePermission):
    def has_permission(self, request, view):
        if request.method == 'DELETE':
            return False
        return check_token(request.headers, False)

    def has_object_permission(self, request, view, obj):
        if request.method == 'DELETE':
            return False
        return check_token(request.headers, False)


class AuthPermission(BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.method == 'DELETE':
            return False
        return check_token(request.headers, False)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.method == 'DELETE':
            return False
        return check_token(request.headers, False)


class LikesAuth(BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.method == 'DELETE':
            return False
        return check_token(request.headers, False)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.method == 'DELETE':
            return False
        return check_token(request.headers, False)


class UserThrottle(SimpleRateThrottle):
    scope = 'user'

    def get_cache_key(self, request, view):
        if check_token(request.headers, False):
            ident = request.headers.get('User')
        else:
            ident = self.get_ident(request)

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }
