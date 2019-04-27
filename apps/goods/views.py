from django.shortcuts import render,redirect
# 导入反向解析的包
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.views.generic import View
# 自定义缓存
from django.core.cache import cache
# 导入django分页类
from django.core.paginator import Paginator
from goods.models import GoodsType, GoodsSKU, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner
# 导入redis的包
from django_redis import get_redis_connection
# 导入评论的类
from order.models import OrderGoods

# Create your views here.

# class Test(object):
#     def __init__(self):
#         self.name = 'abc'
#
# t = Test()
# t.age = 10
# print(t.age)


# http://127.0.0.1:8000
class IndexView(View):
    '''首页'''
    def get(self,request):
        '''显示首页'''
        # 尝试从缓存中获取数据
        # 如果缓存中不存在该对象，则cache.get() 返回None：
        # 下面设置了缓存的 index_page_data是键
        context = cache.get('index_page_data')
        if context is None:
            # 缓存中没有数据
            print('设置缓存')

            # 获取商品的种类信息
            types = GoodsType.objects.all()

            # 获取首页轮播商品信息
            # order_by排序 根据index排序
            goods_banners = IndexGoodsBanner.objects.all().order_by('index') # 升序 0,1,2,3 要降序在index前面加个减号

            # 获取首页促销活动信息
            promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

            # 获取首页分类商品展示信息
            for type in types: # 每一个对象都是GoodsType
                # 查询这个表里面type=type 并且 display_type=1的 order_by用index升序排序
                # (利用外键)
                # 获取type种类首页分类商品的图片展示信息
                image_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')

                # 获取type种类首页分类商品的文字展示信息
                title_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')

                # 动态给type增加属性, 分别保存首页分类商品的图片展示信息和文字展示信息
                type.image_banners = image_banners
                type.title_banners = title_banners

            context = {'types': types,
                       'goods_banners': goods_banners,
                       'promotion_banners': promotion_banners
                       }
        # 设置缓存
        # 基本的接口是和：set(key, value, timeout) get(key)
        # 该timeout参数是可选的，默认为timeout在适当的后端的参数CACHES设置（如上所述）。它是值应存储在缓存中的秒数。在传递
        # None的timeout永远缓存值。一个timeout的0
        # 将不缓存值。
        cache.set('index_page_data', context, 3600)

        # 获取用户购物车商品的数目
        # 拿到用户对象
        user = request.user
        # 购物车商品数目
        cart_count = 0
        # 如果你使用is_authenticated()判断用户是否登录，那么意味着你采用了django的auth系统，
        if user.is_authenticated():
            # 用户已登入
            # 获取一个redis对象 参数是default 所以对应的是redis9好数据库
            conn = get_redis_connection('default')
            # 构造哈希值
            cart_key = 'cart_%d'%user.id
            # 把哈希值的键传入进去 得到商品数目(不包含个数 列苹果10个 草莓10个  这里只会显示2个)
            cart_count = conn.hlen(cart_key)


        # 组织模板上下文
        # 对这个字典进行更新 添加购物车到这个字典里面
        context.update(cart_count=cart_count)

        # 使用模板
        return render(request, 'index.html', context)

# /goods/商品id
class DetailView(View):
    '''详情页'''
    def get(self, request, goods_id):
        '''显示详情页'''
        try:
            sku = GoodsSKU.objects.get(id=goods_id)
        except GoodsSKU.DoesNotExist:
            # 商品不存在
            return redirect(reverse('goods:index'))

        # 获取商品的分类信息
        types = GoodsType.objects.all()

        # 获取商品的评论信息
        # exclude返回不满足条件的数据
        sku_orders = OrderGoods.objects.filter(sku=sku).exclude(comment='')

        # 获取新品信息
        # 就是获取同种类的信息
        # 安创建时间降序排列
        # 取两个
        new_skus = GoodsSKU.objects.filter(type=sku.type).order_by('-create_time')[:2]

        # 获取同一个SPU其他规格的商品(苹果手机 分很多种苹果手机 6 6s 7 7s等)
        # 不要当前的这个 所以把当前这个商品排除
        same_spu_skus = GoodsSKU.objects.filter(goods=sku.goods).exclude(id=goods_id)

        # 获取用户购物车商品的数目
        # 拿到用户对象
        user = request.user
        # 购物车商品数目
        cart_count = 0
        # 如果你使用is_authenticated()判断用户是否登录，那么意味着你采用了django的auth系统，
        if user.is_authenticated():
            # 用户已登入
            # 获取一个redis对象 参数是default 所以对应的是redis9好数据库
            conn = get_redis_connection('default')
            # 构造哈希值
            cart_key = 'cart_%d' % user.id
            # 把哈希值的键传入进去 得到商品数目(不包含个数 列苹果10个 草莓10个  这里只会显示2个)
            cart_count = conn.hlen(cart_key)

            # 添加用户的历史浏览记录
            conn = get_redis_connection('default')
            # 移除 没有的话不做任何操作
            history_key = 'history_%d'%user.id
            # 移除列表中的goods_id 0代表移除全部
            conn.lrem(history_key, 0, goods_id)
            # 把goods_is插入到列表的左侧 也是存在redis里面去
            conn.lpush(history_key, goods_id)
            # 只保存用户最新浏览的5条信息
            conn.ltrim(history_key, 0, 4)


        # 构造上下文
        context = {
            'sku':sku,
            'types':types,
            'sku_orders':sku_orders,
            'new_skus':new_skus,
            'same_spu_skus':same_spu_skus,
            'cart_count':cart_count
        }

        # 使用模板
        return render(request, 'detail.html', context)

# 种类id 对应的页码 排序方式
# restful api-> 请求一种资源
# /list?type_id=种类的id&page=页码&sort=排序方式
# /list/种类id/页码/排序排序方式
# /list/种类id/页码?sort=排序方式
class ListView(View):
    '''列表页面'''
    def get(self, request, type_id, page):
        '''显示列表页'''
        # 获取种类的信息
        try:
            type = GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist:
            # 种类不存在
            return redirect(reverse('goods:index'))

        # 获取商品的分类信息
        types = GoodsType.objects.all()

        # 获取排序的方式
        # sort=default 按照默认id排序
        # sort=price 按照商品价格排序
        # sort=hot 按照商品的销量排序
        sort = request.GET.get('sort')

        if sort == 'price':
            skus = GoodsSKU.objects.filter(type=type).order_by('price')
        elif sort == 'hot':
            skus = GoodsSKU.objects.filter(type=type).order_by('-sales')
        else:
            sort = 'default'
            skus = GoodsSKU.objects.filter(type=type).order_by('-id')

        # 对数据进行分页
        # 第一个参数是可迭代对象 对二哥参数是每页显示的数据条数
        paginator = Paginator(skus, 1)

        # 获取第page页的内容
        try:
            page = int(page)
        except Exception as e:
            page = 1

        # paginator.num_pages 显示总页数
        if page > paginator.num_pages:
            page = 1

        # 返回Page对象 这个对象包含了这一页的所有数据
        # 获取第page页的Page实列对象
        skus_page = paginator.page(page)

        # todo: 进行页码的控制, 页面上最多显示54个页码
        # 1. 总页数小于5页, 页面上显示所有页码
        # 2. 如果当前页是前3页, 显示1-5页
        # 3. 如果当前页是后3页, 显示后5页
        # 4.其他情况, 显示当前页的前2页, 当前页, 当前页的后两页
        # paginator.num_pages 显示总页数
        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages+1)
        elif page <= 3:
            pages = range(1,6)
        elif num_pages - page <= 2:
            pages = range(num_pages-4, num_pages+1)
        else:
            pages = range(page-2, page+3)

        # 获取新品信息
        # 就是获取同种类的信息
        # 安创建时间降序排列
        # 取两个
        new_skus = GoodsSKU.objects.filter(type=type).order_by('-create_time')[:2]

        # 获取用户购物车商品的数目
        # 拿到用户对象
        user = request.user
        # 购物车商品数目
        cart_count = 0
        # 如果你使用is_authenticated()判断用户是否登录，那么意味着你采用了django的auth系统，
        if user.is_authenticated():
            # 用户已登入
            # 获取一个redis对象 参数是default 所以对应的是redis9好数据库
            conn = get_redis_connection('default')
            # 构造哈希值
            cart_key = 'cart_%d' % user.id
            # 把哈希值的键传入进去 得到商品数目(不包含个数 列苹果10个 草莓10个  这里只会显示2个)
            cart_count = conn.hlen(cart_key)

        # 构造上下文
        context = {
            'type':type,
            'types':types,
            'skus_page':skus_page,
            'new_skus':new_skus,
            'cart_count':cart_count,
            'pages':pages,
            'sort':sort
        }

        # 使用模板
        return render(request, 'list.html', context)