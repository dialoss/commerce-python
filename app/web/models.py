import datetime
import json
import time

from django.db import models
from django.db.models import CharField, IntegerField, BooleanField, FloatField, ForeignKey, TextField


class PageMixin(models.Model):
    page = TextField(default='', null=True, blank=True)
    slug = TextField(default='', null=True, blank=True)

    class Meta:
        abstract = True


class MediaMixin(models.Model):
    media = TextField(default='[]', null=True, blank=True)

    class Meta:
        abstract = True


def get_default():
    return int(time.time() * 1000)


class ViewMixin(models.Model):
    viewId = IntegerField(default=get_default, blank=True, null=True, unique=True)

    class Meta:
        abstract = True


class Product(PageMixin, MediaMixin, ViewMixin):
    name = TextField(default='', null=True, blank=True)
    summary = TextField(default='', null=True, blank=True)
    price = FloatField(default=0, blank=True)
    productType = TextField(default='Монтировка', null=True)
    inStock = BooleanField(default=False, blank=True)


class Status(models.Model):
    step = TextField()
    substep = TextField()


class DescriptionMixin(models.Model):
    title = TextField(default='', null=True, blank=True)
    description = TextField(default='', null=True, blank=True)

    class Meta:
        abstract = True


class Order(PageMixin, MediaMixin, ViewMixin, DescriptionMixin):
    product = ForeignKey(Product, on_delete=models.RESTRICT, null=True)
    user = IntegerField(default=None, null=True)
    status = ForeignKey(Status, on_delete=models.RESTRICT, null=True, default=1)
    dateCreated = models.DateTimeField(default=None, null=True, blank=True)
    statusChanged = models.DateTimeField(null=True, default=None)

    def save(self, *args, **kwargs):
        if self.dateCreated is None:
            self.dateCreated = datetime.datetime.now()
        super().save(*args, **kwargs)


class Gallery(MediaMixin, ViewMixin):
    mediaTitle = TextField(default="", blank=True, null=True)
    mediaText = TextField(default="", blank=True, null=True)


class Shop(ViewMixin, DescriptionMixin):
    product = ForeignKey(Product, on_delete=models.CASCADE, null=True)


class Comment(models.Model):
    page = TextField(max_length=100)
    time = models.DateTimeField(default=None, null=True, blank=True)
    text = TextField(max_length=1000, default="", blank=True, null=True)
    parent = IntegerField(default=None, null=True)
    user = IntegerField(default=None)
    media = TextField(default='')

    def save(self, *args, **kwargs):
        if self.time is None:
            self.time = datetime.datetime.now()
        super().save(*args, **kwargs)


class GalleryLikes(models.Model):
    gallery = ForeignKey(Gallery, on_delete=models.CASCADE, null=True)
    user = IntegerField(null=True, default=None, blank=True)


class CommentsLikes(models.Model):
    comment = ForeignKey(Comment, on_delete=models.CASCADE, null=True)
    user = IntegerField(null=True, default=None, blank=True)


class User(models.Model):
    userId = TextField(default='', primary_key=True)
    uuid = TextField(default='')
    messageToken = TextField(default='', blank=True, null=True)
    name = TextField(default='')
    email = TextField(default='')
    telegramId = IntegerField(default=0, null=True)
    deliveryName = TextField(default='', blank=True)
    deliverySurname = TextField(default='', blank=True)
    deliveryLastname = TextField(default='', blank=True)
    deliveryPhone = TextField(default='', blank=True)
    deliveryAddress = TextField(default='', blank=True)

    # notificationNewComment = BooleanField(default=True)
    # notificationOrder = BooleanField(default=True)
    # notificationPush = BooleanField(default=True)

    notificationEmail = BooleanField(default=True)
    notificationTelegram = BooleanField(default=True)
    notificationPush = BooleanField(default=True)


model_mapper = {
    'status': Status,
    'product': Product,
    'order': Order,
    'gallery': Gallery,
    'shop': Shop,
    'user': User,
}

ru = {
    'notificationTelegram': "Уведомления в Telegram",
    'notificationEmail': "Уведомления по почте",
    'notificationPush': "Пуш-уведомления",
    'deliveryName': 'Имя',
    "deliverySurname": "Фамилия",
    "deliveryLastname": "Отчество",
    "deliveryAddress": "Почтовый индекс",
    'deliveryPhone': "Номер телефона",
    "inStock": "В продаже",
    "view": "Вид",
    "summary": "Краткое описание",
    "price": "Цена",
    "model": "Модель",
    'name': "Название",
    'productType': "Тип продукта",
    "status": "Статус заказа",
    'shop': "Описание",
    'title': 'Заголовок',
    "description": "Описание",
    'user': "Пользователь",
    'order': 'Заказ',
    'media': 'Медиа',
    'mediaText': "Описание",
    "mediaTitle": "Заголовок",
    'product': 'Продукт',
    'slug': 'Имя страницы в URL'
}
map = {
    'integer': 'number',
    'bigauto': 'number',
    'float': 'number',
    'text': 'text'
}
defaults_types = {
    'number': 0,
    'text': '',
    'boolean': False,
    'media': [],
}
defaults = {
    "inStock": False,
    "productType": 'Монтировка',
    "status": {'id':1,'step':'Принят',"substep":"Ожидает оплаты"},
    'media': []
}
statuses = [
    ["Принят", "Ожидает оплаты"],
    ["Принят", "Начало изготовления"],
    ["Подготовка материала", "Ожидание доставки"],
    ["Подготовка материала", "Обработка"],
    ["Изготовление деталей"],
    ["Анодирование"],
    ["Покраска"],
    ["Тестирование", "Гидирование"],
    ["Упаковка", "Изготовление упаковки"],
    ["Отправлен получателю"],
    ["Завершён"]
]
statuses = [{"name": " - ".join(statuses[i]), "value": i + 1} for i in range(len(statuses))]

types = ["Монтировка", "Тренога", "Противовес",
         # "Окуляр",
         "Чертёж", "Деталь", "Другое"]
types = [{"name": types[i], "value": types[i], "id": i} for i in range(len(types))]


def gen_schemas():
    models = {}
    all_fields = {}
    for model_name in model_mapper:
        models[model_name] = []
        for field in model_mapper[model_name]._meta.fields:
            data = dict()
            name = field.name
            if all_fields.get(field.name) and data.get('options'):
                name = model_name + "_" + name
            data['name'] = field.name
            data['required'] = not field.null
            t = model_mapper[model_name]._meta.get_field(name).get_internal_type().lower().replace('field', '')
            t = map.get(t, t)
            if not ru.get(name):
                continue
            if name == 'summary' and model_name == 'shop':
                continue
            if name in ["id", 'page', 'dateCreated', 'statusChanged', 'user']:
                continue
            if name in ['product'] and model_name != 'shop':
                continue
            if name in ['mediaTitle', 'mediaText'] and model_name != 'gallery':
                continue

            if name == 'media':
                t = 'media'
            if name == 'shop':
                t = 'bigtext'
            if name == 'productType':
                t = 'select'
                data['choices'] = types

            if name == 'status':
                t = 'select'
                data['choices'] = statuses
            data['type'] = t
            data['label'] = ru.get(name, '')
            data['default'] = defaults.get(name, defaults_types.get(t))

            if t == 'number' and data['default'] is None:
                data['default'] = 0
            if model_name == 'shop' and name == 'inStock':
                data['default'] = True

            models[model_name].append(data)
    open('D:\\Programming\\react-commerce\\src\\api\\schema.json', 'w', encoding='utf-8').write(
        json.dumps(models, ensure_ascii=False))
    open('D:\\Programming\\admin\\src\\api\\schema.json', 'w', encoding='utf-8').write(
        json.dumps(models, ensure_ascii=False))


# try:
gen_schemas()

# except Exception as e:
#     print(e)
#     pass


# for i in statuses:
#     Status.objects.create(step=i[0], substep=i[1] if len(i) == 2 else "")
