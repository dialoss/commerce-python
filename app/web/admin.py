from django.contrib import admin
from .models import *


# Register your models here.


class ProductAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Product._meta.get_fields() if field.name not in ['order', 'media']]
    list_editable = ['inStock', 'price']


class GalleryAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Gallery._meta.get_fields() if field.name]
    # list_editable = [field.name for field in Gallery._meta.get_fields() if field.name]


admin.site.register([Order])
admin.site.register(Product, ProductAdmin)
admin.site.register(Gallery, GalleryAdmin)
