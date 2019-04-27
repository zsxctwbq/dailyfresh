from django.db import models
from django.contrib.auth.models import AbstractUser
from db.base_model import BaseModel
# Create your models here.

# 用户的模型类

class User(AbstractUser, BaseModel):
    '''用户模型类'''

    class Meta:
        db_table = 'df_user'
        verbose_name = '用户'
        verbose_name_plural = verbose_name

# 定义模型管理器类
class AddressManager(models.Manager):
    '''地址模型管理器类'''
    # 1.改变原有查询的结果级:all()
    # 2.封装方法:用户操作模型类对应的数据表(增删改查)
    def get_default_address(self, user):
        '''获取用户的默认收货地址'''
        # self.model:获取self对象所在的模型类
        try:
            # address里的user 等于 user里的user   address里的is_default=True的时候
            # 查到了默认收货地址
            # is_default==True就说明有默认收货地址
            # 这里的self是AddressManager的实例对象 而 这个类又继承model.Manager 所以这里不用写objects 这里的self就相当于是models.Manager的对象
            address = self.get(user=user, is_default=True) # objects默认类型是models.Manager的对象
        except self.model.DoesNotExist:
            # 说明不存在默认收货地址
            address = None

        return address



class Address(BaseModel):
    '''地址模型类'''
    user = models.ForeignKey('User', verbose_name='所属账户')
    receiver = models.CharField(max_length=20, verbose_name='收件人')
    addr = models.CharField(max_length=256, verbose_name='收件地址')
    zip_code = models.CharField(max_length=6, null=True, verbose_name='邮政编码')
    phone = models.CharField(max_length=11, verbose_name='联系电话')
    # is_default默认为False就是没有默认地址 当这个值为True的时候就是有收货地址
    is_default = models.BooleanField(default=False, verbose_name='是否默认')

    # 自定义一个模型管理器对象
    objects = AddressManager()

    class Meta:
        db_table = 'df_address'
        verbose_name = '地址'
        verbose_name_plural = verbose_name
