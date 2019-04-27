# 导入django判断用户是否登录的装饰器
from django.contrib.auth.decorators import login_required

class LoginRequiredMixin(object):
    @classmethod
    def as_view(cls, **initkwargs):
        # 调用父类的as_views (相当于路径哪里的类名.as_view())
        view = super(LoginRequiredMixin, cls).as_view(**initkwargs)
        # 这里就是判断用户登录了没 跟路径哪里一样 这样就可以把路径哪里的去掉 路径哪里按原来那样写
        return login_required(view)