from django.contrib import admin
# 导入自定义的缓存 操作类
from django.core.cache import cache
from goods.models import GoodsType, GoodsSKU, Goods, GoodsImage, IndexGoodsBanner, IndexTypeGoodsBanner, IndexPromotionBanner
# 商品类型模型类
# 商品SKU模型类
# 商品SPU模型类
# 商品图片模型类
# 首页轮播商品展示模型类
# 首页分类商品展示模型类
# 首页促销活动模型类

class BaseModelAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        '''admin后台新增或者更新表中的数据时调用'''
        # 调用父类的这个方法
        super().save_model(request, obj, form, change)

        # 发送任务, 让celery worker重新生成首页静态页面
        from celery_tasks.tasks import generate_static_index_html
        generate_static_index_html.delay()

        # 清楚首页的缓存存储
        # 删除缓存
        cache.delete('index_page_data')



    def delete_model(self, request, obj):
        '''admin删除表中的数据是调用'''
        # 调用父类的这个方法
        super().delete_model(request, obj)

        # 发送任务, 让celery worker重新生成静态页面
        from celery_tasks.tasks import generate_static_index_html
        generate_static_index_html.delay()

        # 清楚首页的缓存存储
        # 删除缓存
        cache.delete('index_page_data')


class GoodsTypeAdmin(BaseModelAdmin):
    list_display = ['name', 'logo', 'image']

class GoodsSKUAdmin(BaseModelAdmin):
    list_display = ['type', 'goods', 'name', 'desc', 'price', 'unite', 'image', 'stock', 'sales', 'status']

class GoodsAdmin(BaseModelAdmin):
    list_display = ['name', 'detail']

class GoodsImageAdmin(BaseModelAdmin):
    list_display = ['sku', 'image']

class IndexGoodsBannerAdmin(BaseModelAdmin):
    list_display = ['sku', 'image', 'index']

class IndexTypeGoodsBannerAdmin(BaseModelAdmin):
    list_display = ['type', 'sku', 'display_type', 'index']

class IndexPromotionBannerAdmin(BaseModelAdmin):
    list_display = ['name', 'url', 'image', 'index']


admin.site.register(GoodsType, GoodsTypeAdmin)
admin.site.register(GoodsSKU, GoodsSKUAdmin)
admin.site.register(Goods, GoodsAdmin)
admin.site.register(GoodsImage, GoodsImageAdmin)
admin.site.register(IndexGoodsBanner, IndexGoodsBannerAdmin)
admin.site.register(IndexTypeGoodsBanner, IndexTypeGoodsBannerAdmin)
admin.site.register(IndexPromotionBanner, IndexPromotionBannerAdmin)

