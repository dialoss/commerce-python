import json
import time
import urllib.parse
from datetime import datetime
from threading import Thread

import requests
from django.db.models import Q
from django.forms import model_to_dict
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import generics, mixins, permissions, status
from rest_framework.decorators import api_view
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.viewsets import ModelViewSet, GenericViewSet

from app.settings import ADMIN_ID
from fcm import send, send_email, _send_email
from notifications import Notification
from test import scraper
from web.google_drive import GoogleAuthentication
from web.models import *
from web.permissions import OwnerPermission, AuthPermission, LikesAuth, UserThrottle, check_token, get_user, \
    CreateOnly, ReadOnly, AdminPermission
from web.serializer import *


class BaseAPI(ModelViewSet):
    permission_classes = [
        AdminPermission
    ]


class OwnerAPI(ModelViewSet):
    throttle_classes = [UserThrottle]
    permission_classes = [
        OwnerPermission
    ]


class AuthorizedAPI(ModelViewSet):
    throttle_classes = [UserThrottle]
    permission_classes = [
        AuthPermission
    ]


def notify(userId, type, data):
    def task():
        user = User.objects.get(userId=userId)
        n = Notification(user, type, data)
        if user.notificationEmail: n.email()
        if user.notificationPush: n.push()
        if user.notificationTelegram: n.telegram()

    Thread(target=task).start()


def change_status(order_id, status_id):
    order = Order.objects.get(id=order_id)
    if status_id and order.status.id != status_id:
        user = User.objects.get(userId=order.user)
        status = Status.objects.get(id=status_id)
        st = status.step
        if status.substep:
            st += ' - ' + status.substep
        notify(order.user, 'order', {
            'title': f"Изменение статуса заказа {order.product.productType} {order.product.name}",
            'body': st,
            'link': f"https://www.mymountmt.ru/orders/{order.id}-{user.name.replace(' ', '').lower()}",
        })
        Order.objects.filter(id=order_id).update(statusChanged=datetime.now())


class SlugView(ModelViewSet):
    def retrieve(self, request, *args, **kwargs):
        slug = request.query_params.get('slug')
        if slug:
            instance = self.queryset.filter(slug=slug)
            if len(instance):
                serializer = self.get_serializer(instance[0])
                return Response(serializer.data)

        return super().retrieve(request, args, kwargs)


class OrderAPI(AuthorizedAPI, SlugView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(name='user', location=OpenApiParameter.QUERY, description='User',
                             required=False, type=int),
            OpenApiParameter(name='productType', location=OpenApiParameter.QUERY, description='Order productType',
                             required=False, type=str),
            OpenApiParameter(name='status', location=OpenApiParameter.QUERY,
                             description='Orders status not equal to given',
                             required=False, type=int),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, args, kwargs)

    def update(self, request, *args, **kwargs):
        for i in ['status', 'product']:
            if request.data.get(i):
                request.data[i] = request.data[i]['id']
        s = request.data.get('status')
        if request.data.get('id'):
            try:
                change_status(request.data['id'], s)
            except:
                pass
        return super().update(request, args, kwargs)

    def create(self, request, *args, **kwargs):
        for i in ['status', 'product']:
            if request.data.get(i):
                if not isinstance(request.data[i], int):
                    request.data[i] = request.data[i]['id']
        if isinstance(request.data.get('product'), int):    
            product = Product.objects.get(id=request.data['product'])
            data = {
                "product": product,
                'media': product.media,
                'title': product.productType + " " + product.name,
                'description': product.summary,
                'user': get_user(request.headers)[0]['userId']
            }
            user = User.objects.get(userId=data['user'])
            order = Order.objects.create(**data)
            notify(ADMIN_ID, 'order', {
                'title': f"Новый заказ {order.product.productType} {order.product.name}",
                'body': f"От {user.name} {user.email}",
                'link': f"https://www.mymountmt.ru/orders/{order.id}-{user.name.replace(' ', '').lower()}",
            })
            return Response(model_to_dict(order))
        else:
            return super().create(request, args, kwargs)

    def get_queryset(self):
        user = self.request.query_params.get('user')
        type = self.request.query_params.get('productType')
        status = self.request.query_params.get('status')
        s = Order.objects.all()
        if user:
            s = s.filter(user=user)
        if type:
            s = s.filter(Q(product__productType=type) | Q(product=None))
        if status:
            if status[0] == '!':
                s = s.filter(~Q(status=status[1:]))
            else:
                s = s.filter(status=status)
        return s


class ProductAPI(BaseAPI, SlugView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(name='productType', location=OpenApiParameter.QUERY, description='Product type',
                             required=False, type=str),
        ],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, args, kwargs)

    def get_queryset(self):
        type = self.request.query_params.get('productType')
        if type:
            return Product.objects.filter(productType=type.capitalize())
        return Product.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        if request.data.get('inStock'):
            Shop.objects.create(product=instance, title=instance.productType + " " + instance.name,
                                description=instance.summary)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        if request.data.get('inStock'):
            if not instance.inStock and request.data['inStock'] == True:
                Shop.objects.create(product=instance, title=instance.productType + " " + instance.name,
                                    description=instance.summary)
            if instance.inStock and request.data['inStock'] == False:
                Shop.objects.get(product=instance).delete()

        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)


class Likeable(ModelViewSet):
    @extend_schema(
        parameters=[
            OpenApiParameter(name='like', location=OpenApiParameter.QUERY, description='Like item',
                             required=False, type=str),
        ],
    )
    def update(self, request, *args, **kwargs):
        if request.query_params.get('like'):
            instance = self.get_object()
            u = get_user(request.headers)[0].get('userId')
            data = {self.likes_key: instance, 'user': u}
            if not len(self.likes_class.objects.filter(**data)):
                like = self.likes_class.objects.create(**data)
                user = User.objects.get(userId=u)
                notify(ADMIN_ID, 'like', {
                    'title': 'Новый лайк',
                    'body': f'Пользователю {user.name} {user.email} ' + self.likes_notify,
                    'link': 'https://www.mymountmt.ru/' + self.likes_link(instance) + "#" + str(instance.id),
                })
                return OK
        return super().update(request, args, kwargs)


class GalleryAPI(Likeable):
    queryset = Gallery.objects.all()
    serializer_class = GallerySerializer
    likes_key = "gallery"
    likes_class = GalleryLikes
    likes_notify = 'понравилась запись в галерее'
    permission_classes = [ AdminPermission]

    def likes_link(self, i): return "gallery"


class ShopAPI(BaseAPI):
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        # Shop.objects.filter(id=serializer.data['id']).update(product=product_instance)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class StatusAPI(BaseAPI):
    queryset = Status.objects.all()
    serializer_class = StatusSerializer


class UserAPI(OwnerAPI):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def update(self, request, *args, **kwargs):
        data = request.data
        id = kwargs.get('pk')
        if not id or id == 'undefined':
            return JsonResponse({})
        u = User.objects.filter(userId=id)

        if not len(u):
            u = User.objects.create(**data)
            notify(ADMIN_ID, 'user', {
                'title': 'Новый пользователь зарегистрирован',
                'body': f'Имя {u.name} Почта {u.email}',
                'link': ''
            })
        else:
            u.update(**data)
        return JsonResponse({})


class CommentAPI(Likeable):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    likes_key = "comment"
    likes_class = CommentsLikes
    likes_notify = 'понравился комментарий'
    permission_classes = [CreateOnly|ReadOnly|AdminPermission]

    def likes_link(self, instance):
        return instance.page

    @extend_schema(
        parameters=[
            OpenApiParameter(name='page', location=OpenApiParameter.QUERY, description='Page',
                             required=True, type=str),
            OpenApiParameter(name='start', location=OpenApiParameter.QUERY, description='Comments tree start',
                             required=True, type=int),
        ],
    )
    def list(self, request, *args, **kwargs):
        page = request.query_params.get('page')
        limit = request.query_params.get('limit', '15')
        offset = request.query_params.get('offset', '0')
        start = request.query_params.get('start', '-1')
        limit = int(limit)
        offset = int(offset)
        start = int(start)

        page = urllib.parse.unquote(page)
        comms = Comment.objects.filter(page=page)
        data = {}
        for com in comms:
            p = com.parent or -1
            if not data.get(p):
                data[p] = []
            data[p].append(com)
        for p in data:
            data[p].sort(key=lambda x: x.id)
        if -1 in data:
            data[-1].sort(key=lambda x: -x.id)
        counter = 0
        end_com = None
        result = []
        end_dfs = False

        def dfs(cur):
            nonlocal counter, end_com, end_dfs
            for child in data.get(cur, []):
                if counter > limit:
                    end_dfs = True
                    return
                end_com = child
                counter += 1
                result.append(child)
                dfs(child.id)

        cur = start
        while True:
            dfs(cur)
            if end_dfs:
                break
            try:
                parent = Comment.objects.get(id=cur).parent or -1
            except:
                break
            childs = data[parent]
            childs_to_visit = []
            for c in childs:
                if parent == -1:
                    if c.id < cur:
                        childs_to_visit.append(c)
                else:
                    if c.id > cur:
                        childs_to_visit.append(c)
            data[parent] = childs_to_visit
            cur = parent

        serializer = CommentSerializer(result, many=True)
        return Response({
            'results': serializer.data,
            'count': len(comms),
        })
        # return Response({
        #     'results': CommentSerializer(Comment.objects.filter(page=page), many=True).data
        # })

    def create(self, request, *args, **kwargs):
        data = request.data
        user = get_user(request.headers)[0]['userId']
        data['user'] = user

        comm = Comment.objects.create(**data)
        user = model_to_dict(User.objects.get(userId=user))
        notify(ADMIN_ID, 'comment', {
            'title': "Новый комментарий от " + user['name'] + ' ' + user['email'],
            'body': data['text'],
            'link': "https://www.mymountmt.ru/" + data['page'],
            'page': data['page'],
            'user': user
        })

        comm_s = CommentSerializer(instance=comm).data
        return Response(comm_s)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if len(Comment.objects.filter(parent=instance.id)):
            return Response(status=400)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


OK = JsonResponse(data={"ok": True}, status=200)
ERROR = JsonResponse(data={"ok": False}, status=400)


@csrf_exempt
def check_income(request):
    data = request.POST
    id = data['label']
    change_status(id, 2)
    return OK


endpoint_mapper = {
    'status': StatusAPI,
    'product': ProductAPI,
    'order': OrderAPI,
    'gallery': GalleryAPI,
    'shop': ShopAPI,
    'user': UserAPI,
}


@api_view(['POST'])
@csrf_exempt
def reorder(request):
    if not check_token(request.headers): return ERROR
    data = request.data
    e = data['endpoint']
    order = data['order']
    prev = data['initItems']
    model = model_mapper[e]
    for o in prev:
        if o['viewId'] not in order:
            try:
                model.objects.filter(id=o['id']).delete()
            except:
                pass

    id = int(time.time() * 1000)
    items = []
    for i in order:
        model.objects.filter(viewId=i).update(viewId=id)
        items.append(model.objects.get(viewId=id))
        id += 1
    serializer = endpoint_mapper[e].serializer_class
    data = serializer(instance=items, many=True).data
    return Response(data)


@api_view(["POST"])
@csrf_exempt
def upload_model(request):
    data = request.data
    requests.post(
        CLOUDINARY_URL,
        data['file'],
        data={"context": "model=" + data['model']})
    return OK


@api_view(["POST"])
@csrf_exempt
def test(request):
    d = request.data
    open('result/' + d['page'], 'w', encoding='utf-8').write(json.dumps(d['data'], ensure_ascii=False))
    return OK


@api_view(["GET"])
@csrf_exempt
def google(request):
    return JsonResponse(GoogleAuthentication.get_credentials())
