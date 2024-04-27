from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from web.models import *
from django.utils.html import escape


class GalleryLikesSerializer(ModelSerializer):
    class Meta:
        model = GalleryLikes
        fields = "__all__"


class CommentLikesSerializer(ModelSerializer):
    class Meta:
        model = CommentsLikes
        fields = "__all__"


class GallerySerializer(ModelSerializer):
    class Meta:
        model = Gallery
        fields = "__all__"

    def to_representation(self, instance):
        likes = GalleryLikes.objects.filter(gallery=instance)
        s = super().to_representation(instance)
        s['likes'] = GalleryLikesSerializer(instance=likes, many=True).data
        return s


class PageSerializer(ModelSerializer):
    def to_representation(self, instance):
        s = super().to_representation(instance)
        if self.context.get('request') and not self.context['request'].parser_context['kwargs'].get('pk'):
            del s['page']

        return s


class ProductSerializer(PageSerializer):
    class Meta:
        model = Product
        fields = "__all__"


class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"


class StatusSerializer(ModelSerializer):
    class Meta:
        model = Status
        fields = "__all__"


class OrderSerializer(PageSerializer):
    class Meta:
        model = Order
        fields = "__all__"

    def to_representation(self, instance):
        self.fields['product'] = ProductSerializer(read_only=True)
        self.fields['status'] = StatusSerializer(read_only=True)

        return super().to_representation(instance)


class ShopSerializer(ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = Shop
        fields = "__all__"


class CommentSerializer(ModelSerializer):
    class Meta:
        model = Comment
        fields = "__all__"

    def validate_text(self, value):
        return escape(value)

    def to_representation(self, instance):
        likes = CommentsLikes.objects.filter(comment=instance)
        s = super().to_representation(instance)
        s['likes'] = CommentLikesSerializer(instance=likes, many=True).data
        return s
