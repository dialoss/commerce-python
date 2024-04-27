from rest_framework.routers import SimpleRouter

from web.views import *

router = SimpleRouter()
router.register(r"product", ProductAPI)
router.register(r"order", OrderAPI)
router.register(r"gallery", GalleryAPI)
router.register(r"shop", ShopAPI, basename="shop")
router.register(r"comment", CommentAPI)
router.register(r"status", StatusAPI)
router.register(r"user", UserAPI)