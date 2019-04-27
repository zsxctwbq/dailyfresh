from django.conf.urls import url
# 导入django判断用户是否登录的装饰器
from django.contrib.auth.decorators import login_required
from user.views import RegisterView, ActiveView, LoginView, UserInfoView, UserOrderView, AddressView, LogoutView

urlpatterns = [
    # url(r'^register$', views.register,name='register'),# 注册
    # url(r'^register_handle$', views.register_handle, name='register_handle'), # 注册处理

    # 根据你相应的请求方式 配置相应的视图
    url(r'^register$', RegisterView.as_view(), name='register'), # 注册

    url(r'^active/(?P<token>.*)$', ActiveView.as_view(), name='active'), # 用户激活

    url(r'^login$', LoginView.as_view(), name='login'), # 登录

    url(r'^logout$', LogoutView.as_view(), name='logout'), # 注销登入

    # login_required判断用户登入了就调用里面的函数
    # 如果没登入则重定向到/accounts/login/?next=你输入的地址
    # 没登入时默认跳转到settings.LOGIN_URL 但是我们这里要他跳转到我们的页面 所以要去修改他的设置
    # url(r'^$', login_required(UserInfoView.as_view()), name='user'), # 用户中心-信息页
    #
    # url(r'^order$', login_required(UserOrderView.as_view()), name='order'), # 用户中心-订单页
    #
    # url(r'^address$', login_required(AddressView.as_view()), name='address'), # 用户中心-地址页

    # 这里的as_view()是utils下的LoginRequiredMixin下的as_view()方法
    url(r'^$', UserInfoView.as_view(), name='user'), # 用户中心-信息页

    url(r'^order/(?P<page>\d+)$', UserOrderView.as_view(), name='order'), # 用户中心-订单页

    url(r'^address$', AddressView.as_view(), name='address'), # 用户中心-地址页



]