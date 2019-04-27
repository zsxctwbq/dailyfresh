from django.db import models
from db.base_model import BaseModel
# Create your models here.

# 订单的模型类

class OrderInfo(BaseModel):
    '''订单模型类'''

    PAY_METHODS = {
        '1': "货到付款",
        '2': "微信支付",
        '3': "支付宝",
        '4': '银联支付'
    }

    PAY_METHODS_ENUM = {
        "CASH": 1,
        "ALIPAY": 2
    }

    ORDER_STATUS_ENUM = {
        "UNPAID": 1,
        "UNSEND": 2,
        "UNRECEIVED": 3,
        "UNCOMMENT": 4,
        "FINISHED": 5
    }

    PAY_METHOD_CHOICES = (
        (1, '货到付款'),
        (2, '微信支付'),
        (3, '支付宝'),
        (4, '银联支付')
    )

    ORDER_STATUS = {
        1:'待支付',
        2:'待发货',
        3:'待收货',
        4:'待评价',
        5:'已完成'
    }

    ORDER_STATUS_CHOICES = (
        (1, '待支付'),
        (2, '待发货'),
        (3, '待收货'),
        (4, '待评价'),
        (5, '已完成')
    )

    order_id = models.CharField(max_length=128, primary_key=True, verbose_name='订单id')
    user = models.ForeignKey('user.User', verbose_name='用户')
    addr = models.ForeignKey('user.Address', verbose_name='地址')
    pay_method = models.SmallIntegerField(choices=PAY_METHOD_CHOICES, default=3, verbose_name='支付方式')
    total_count = models.IntegerField(default=1, verbose_name='商品数量')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='商品总价')
    # models.DecimalField(max_digits=None, decimal_places=None[, **options])
    # 使用    Decimal   实例表示固定精度的十进制数的字段。它有两个必须的参数：   max_digits：数字允许的最大位数
    # decimal_places：小数的最大位数    例如，要存储的数字最大长度为3位，而带有两个小数位，可以使用：
    # models.DecimalField(max_digits=3, decimal_places=2, ...)
    transit_price = models.DecimalField(max_digits=10, decimal_places=2,verbose_name='订单运费')
    # 这里用的SmallIntegerField它里面的choices属性 是给你自己选状态的
    # class UserInfo(models.Model):
    #     gender_choices = (
    #         (1, "男"),
    #         (2, "女"),
    #         (3, "保密"))
    #     gender = models.SmallIntegerField(verbose_name="性别", choices=gender_choices)
    # 我们在前端显示的是
    # "男"、"女"、"保密"，而不是1、2、3，则需要拿到这张表的对象（obj），使用 obj.get_字段名_display() 即可。
    order_status = models.SmallIntegerField(choices=ORDER_STATUS_CHOICES, default=1, verbose_name='订单状态')
    trade_no = models.CharField(max_length=128, default='', verbose_name='支付编号')

    class Meta:
        db_table = 'df_order_info'
        verbose_name = '订单'
        verbose_name_plural = verbose_name


class OrderGoods(BaseModel):
    '''订单商品模型类'''
    order = models.ForeignKey('OrderInfo', verbose_name='订单')
    sku = models.ForeignKey('goods.GoodsSKU', verbose_name='商品SKU')
    count = models.IntegerField(default=1, verbose_name='商品数目')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='商品价格')
    comment = models.CharField(max_length=256, default='', verbose_name='评论')

    class Meta:
        db_table = 'df_order_goods'
        verbose_name = '订单商品'
        verbose_name_plural = verbose_name