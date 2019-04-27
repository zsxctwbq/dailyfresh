from django.shortcuts import render,redirect
from django.http import HttpResponse
from django.core.urlresolvers import reverse
# 导入发送邮件的模块
from django.core.mail import send_mail
# 导入django认证系统 authenticate认证用户信息跟你登入的信息是否一致
# login()使用Django的会话框架将用户的ID保存在会话中 该方法会为将user_id以及user_backend放入session中存储
# logout()要注销已登录的用户 django.contrib.auth.login()，请django.contrib.auth.logout()在您的视图中使用 。它需要一个 HttpRequest对象并且没有返回值
from django.contrib.auth import authenticate, login, logout
# 导入分页类
from django.core.paginator import Paginator
# 导入类视图
from django.views.generic import View
from django.conf import settings
from user.models import User, Address
from goods.models import GoodsSKU
# 导入订单模型了
from order.models import OrderInfo, OrderGoods
# 导入发送邮件的函数
from celery_tasks.tasks import send_register_active_email
# 这个类帮忙实现加密 还可以发起链接的激活时间过了时间链接无效
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
# 这是过期异常
from itsdangerous import SignatureExpired
# 倒入django里面判断用户名是否登陆的装饰器
from utils.mixin import LoginRequiredMixin
# 导入django_redis里面拿redis在setting的配置包
from django_redis import get_redis_connection
import re

# /user/register
# GET POST PUT DELETE OPTION
def register(request):
    ''' 显示注册页面 '''
    if request.method == 'GET':
        # 显示注册页面
        return render(request,'register.html')
    else:
        # 进行注册处理
        # 接收数据
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')

        # 进行数据的校验
        # 里面的数据用数据为空是成立
        if not all([username, password, email]):
            # 数据不完整
            return render(request, 'register.html', {'errmsg': '数据不完整'})
            # return HttpResponse('数据error')

        # 校验邮箱
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})
            # return HttpResponse('邮箱error')

        # 校验checkbox 被点击时才是on
        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意协议'})
            # return HttpResponse('请用一协议')

        # 校验用户名是否重复 不校验下面会报错
        # get查不到时报异常
        # 这里记住了python跟c++ java都不同 python变量只要是在同一函数里就能用 没有什么if作用于等 try作用域等
        try:
            # 查询这个数据库里username==接收到的username
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # 用户名不存在
            user = None

        if user:
            # 用户名已存在
            return render(request, 'register.html', {'errmsg': '用户名已存在'})

        # 进行业务处理:进行用户注册
        # django的认证系统没有必要在一个个赋值 直接把接收的数据丢进去
        # 在此注册的时候如果有这个用户名它就会报错
        user = User.objects.create_user(username, email, password)
        # django的认证系统他帮我们激活了 这里我不能让他激活
        user.is_active = 0
        user.save()

        # 返回应答, 跳转到首页
        # redirect 重定向跳转页面
        # reverse 反向解析
        return redirect(reverse('goods:index'))


def register_handle(request):
    ''' 进行注册的处理 '''
    # 接收数据
    username = request.POST.get('user_name')
    password = request.POST.get('pwd')
    email = request.POST.get('email')
    allow = request.POST.get('allow')

    # 进行数据的校验
    # 里面的数据用数据为空是成立
    if not all([username,password,email]):
        # 数据不完整
        return render(request,'register.html',{'errmsg':'数据不完整'})
        # return HttpResponse('数据error')

    # 校验邮箱
    if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$',email):
        return render(request,'register.html',{'errmsg':'邮箱格式不正确'})
        # return HttpResponse('邮箱error')

    # 校验checkbox 被点击时才是on
    if allow != 'on':
        return render(request, 'register.html', {'errmsg':'请同意协议'})
        # return HttpResponse('请用一协议')

    # 校验用户名是否重复 不校验下面会报错
    # get查不到时报异常
    # 这里记住了python跟c++ java都不同 python变量只要是在同一函数里就能用 没有什么if作用于等 try作用域等
    try:
        # 查询这个数据库里username==接收到的username
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        # 用户名不存在
        user = None

    if user:
        # 用户名已存在
        return render(request,'register.html',{'errmsg':'用户名已存在'})

    # 进行业务处理:进行用户注册
    # django的认证系统没有必要在一个个赋值 直接把接收的数据丢进去
    # 在此注册的时候如果有这个用户名它就会报错
    user = User.objects.create_user(username, email, password)
    # django的认证系统他帮我们激活了 这里我不能让他激活
    user.is_active = 0
    user.save()


    # 返回应答, 跳转到首页
    # redirect 重定向跳转页面
    # reverse 反向解析
    return redirect(reverse('goods:index'))

# 注册的类视图
class RegisterView(View):
    ''' 注册 '''
    # get方式访问
    def get(self, request):
        ''' 显示注册页面 '''
        return render(request, 'register.html')

    def post(self, request):
        ''' 进行注册处理 '''
        # 进行注册处理
        # 接收数据
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')

        # 进行数据的校验
        # 里面的数据用数据为空是成立
        if not all([username, password, email]):
            # 数据不完整
            return render(request, 'register.html', {'errmsg': '数据不完整'})
            # return HttpResponse('数据error')

        # 校验邮箱
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})
            # return HttpResponse('邮箱error')

        # 校验checkbox 被点击时才是on
        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意协议'})
            # return HttpResponse('请用一协议')

        # 校验用户名是否重复 不校验下面会报错
        # get查不到时报异常
        # 这里记住了python跟c++ java都不同 python变量只要是在同一函数里就能用 没有什么if作用于等 try作用域等
        try:
            # 查询这个数据库里username==接收到的username
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # 用户名不存在
            user = None

        if user:
            # 用户名已存在
            return render(request, 'register.html', {'errmsg': '用户名已存在'})

        # 进行业务处理:进行用户注册
        # django的认证系统没有必要在一个个赋值 直接把接收的数据丢进去
        # 在此注册的时候如果有这个用户名它就会报错
        user = User.objects.create_user(username, email, password)
        # django的认证系统他帮我们激活了 这里我不能让他激活
        user.is_active = 0
        user.save()

        # 发送激活邮件, 包含激活的链接: http://172.16.66.228:8000/user/active/1 1是id
        # 激活连接中需要包含用户的身份信息,并且要把身份信息进行加密处理

        # 加密用户的身份信息, 生成激活token
        # 借助django的setting里的SECRET_KEY
        # 把SECRET_KEY设置为秘钥
        # 3600s后过期
        serializer = Serializer(settings.SECRET_KEY, 3600)
        info = {'confirm':user.id}
        token = serializer.dumps(info) # bytes数据
        # 把bytes数据转换成 utf-8的字符串
        token = token.decode('utf-8')

        # 发邮件
        # 看celery_tasks这个目录的tasks这个文件
        # 发送到redis队列里面 需要任务处理着监听任务队列
        send_register_active_email.delay(email, username, token)

        # 返回应答, 跳转到首页
        # redirect 重定向跳转页面
        # reverse 反向解析
        return redirect(reverse('goods:index'))




class ActiveView(View):
    ''' 用户激活 '''
    def get(self, request, token):
        ''' 进行用户激活 '''
        # 进行解密, 获取要激活的用户信息
        # 重要秘钥和过期时间是一样 就可以解上面的密
        serializer = Serializer(settings.SECRET_KEY, 3600)
        try:
            info = serializer.loads(token)
            # 获取待激活用户的id
            user_id = info['confirm']

            # 根据id获取用户信息
            user = User.objects.get(id=user_id)
            # is_active是数据库里面用户的激活状态
            user.is_active = 1
            user.save()

            # 跳转到登入页面
            return redirect(reverse('user:login'))
        except SignatureExpired as e:
            # 激活链接已过期
            return HttpResponse('激活链接已过期')

 # /user/login
class LoginView(View):
    ''' 登入 '''
    def get(self,request):
        ''' 显示登入页面 '''
        # 判断是否记住了用户名
        # 判断次页面有没有cookie里有没有'username'这个cookie键
        if 'username' in request.COOKIES:
            # 有就获取这个键的值
            username = request.COOKIES.get('username')
            # 把checked赋值给checked 这个值传给页面那么页面记住用户名哪里是默认被选中的
            checked = 'checked'
        else:
            username = ''
            checked = ''

        # 使用模板 把构造上下文传到页面去
        return render(request, 'login.html', {'username':username, 'checked':checked})

    def post(self, request):
        ''' 登入校验 '''
        # 接收数据
        username = request.POST.get('username')
        password = request.POST.get('pwd')

        # 校验数据
        if not all([username, password]):
            return render(request, 'login.html', {'errmsg':'数据不完整'})

        # 业务处理:登录校验
        # 返回应答

        # 这是老办法别用了
        # user = User.objects.get(username=username, password=password)
        # django认证系统 认证用户信息是否正确
        user = authenticate(username=username, password=password)
        if user is not None:
            # 用户名密码正确
            if user.is_active:
                # 用户已激活
                # 记录用户的登入状态
                # 这里的login就相当于session 这里调用了django的认证系统
                # login()使用django的session框架来将用户的id保存在session中
                login(request, user)

                # 获取登录后所要跳转到的地址
                # 默认跳转到首页
                # 这个位置next只能是空 要不然它url地址路径通不过
                # 是想记住用户上次没登入访问的网址next可以提取出来
                next_url = request.GET.get('next', reverse('goods:index')) # 直接访问是返回None 但是我们给了一个默认值reverse重定向
                # 跳转到next_url这个地址
                # response记住里这个页面的所有东西(响应报文)
                response = redirect(next_url) # HttpResponseRedirect

                # 判断是否需要记住用户名
                remember = request.POST.get('remember')
                # 用户勾选了你拿到的是on 没有勾选你拿到的是None
                if remember == 'on':
                    # 记住用户名 记住3天
                    # 在response这个页面里设置cookie
                    # cookie是存在浏览器本地的不管在那个页面本地都有cookie 除非它过期
                    response.set_cookie('username', username, max_age=7*24*3600)
                else:
                    # 把这个页面的cookie删除
                    response.delete_cookie('username')

                # 返回response(这个页面)
                return response

            else:
                # 用户未激活
                return render(request, 'login.html', {'errmsg':'账户未激活'})
        else:
            # 用户名或密码错误
            return render(request, 'login.html', {'errmsg':'用户名或密码错误'})

# /user/logout
class LogoutView(View):
    '''退出登入'''
    def get(self, request):
        '''退出登入'''
        # 清楚用户的session信息
        logout(request)

        # 跳转到首页
        return redirect(reverse('goods:index'))



# /user
# 他继承了两个父类 它现在要从前面开始找
class UserInfoView(LoginRequiredMixin, View):
    '''用户中心-信息页'''
    def get(self,request):
        '''显示'''
        # page='user'

        # 如果用户登录-->User类的实列
        # 如果用户未登录-->AnonymousUser类的实列
        # request.user.is_authenticated() 判断用户登录没 登录的用户返回True 没登录返回False{
        #       AnonymousUser.is_authenticated()是False
        #       User.is_authenticated()是True
        #       这两个实列都有这个方法
        # }

        # 获取用户的个人信息
        user = request.user
        address = Address.objects.get_default_address(user)
        # 获取用户的历史浏览记录
        # 导入与python交互的包
        from redis import StrictRedis
        # 这里的host写你在setting配置缓存时的那个ip和port db(配置的那个数据库)
        # sr = StrictRedis(host='172.16.66.228', port='6379', db=9)

        # con 等同上面的sr
        # 这里参数是default 对应的是redis9好数据库
        con = get_redis_connection('default')

        # 取出用户的历史浏览记录
        history_key = 'history_%d'%user.id

        # 获取用户最新浏览的5个商品id
        sku_ids = con.lrange(history_key, 0,4)

        # 从数据库中查询用户浏览的商品的具体信息
        # goods_li = GoodsSKU.objects.filter(id__in=sku_ids)
        #
        # goods_res = []
        # # 遍历最新拿到的5个商品的id
        # for a_id in sku_ids:
        #     # 遍历这些商品
        #     for goods in goods_li:
        #         # 第一个id等于某一个商品的id时把它添加到这个列表
        #         if a_id == goods.id:
        #             goods_res.append(goods)

        # 不建议使用上面方法
        # 用下面这个方法
        goods_li = []
        for id in sku_ids:
            # 把拿到的id 找到对应的商品
            goods = GoodsSKU.objects.get(id=id)
            # 把商品添加到商品列表后面
            goods_li.append(goods)

        # 组织上下文
        context = {'page':'user',
                   'address':address,
                    'goods_li':goods_li
                   }


        # 除了你给模板文件传递的模板变量之外, django框架会把request.user也传给模板文件
        return render(request, 'user_center_info.html', context)

# /user/order
# 他继承了两个父类 它现在要从前面开始找
class UserOrderView(LoginRequiredMixin, View):
    '''用户中心-订单页'''
    def get(self,request, page):
        '''显示'''
        # 获取用户的订单信息
        user = request.user
        # 查寻用户的所有订单根据创建时间排序
        orders = OrderInfo.objects.filter(user=user).order_by('-create_time')

        # 遍历获取订单商品的信息
        # OrderInfo对象
        for order in orders:
            # 根据order_id查询订单商品的信息
            # OrderGoods对象集
            order_skus = OrderGoods.objects.filter(order=order.order_id)

            # 遍历order_skus计算商品的小计
            for order_sku in order_skus:
                # 计算小计
                amount = order_sku.count * order_sku.price
                #动态给这个order_sku增加属性amount, 保存订单商品的小计
                order_sku.amount = amount

            # 动态给这个order增加属性, 保存订单状态标题
            order.status_name = OrderInfo.ORDER_STATUS[order.order_status]
            # 动态给这个order增加属性, 保存订单商品的信息
            order.order_skus = order_skus

        # 分页
        # 对orders进行分页, 每页显示一条订单数据
        paginator = Paginator(orders, 1)

        # 处理页码
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
        # 获取当前页要显示的商品对象
        order_page = paginator.page(page)

        # todo: 进行页码的控制, 页面上最多显示54个页码
        # 1. 总页数小于5页, 页面上显示所有页码
        # 2. 如果当前页是前3页, 显示1-5页
        # 3. 如果当前页是后3页, 显示后5页
        # 4.其他情况, 显示当前页的前2页, 当前页, 当前页的后两页
        # paginator.num_pages 显示总页数
        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages + 1)
        elif page <= 3:
            pages = range(1, 6)
        elif num_pages - page <= 2:
            pages = range(num_pages - 4, num_pages + 1)
        else:
            pages = range(page - 2, page + 3)

        # 组织上写文
        context = {
            'order_page':order_page,
            'pages':pages,
            'page': 'order'
        }

        # 使用模板
        return render(request, 'user_center_order.html', context)

# /user/address
# 他继承了两个父类 它现在要从前面开始找
class AddressView(LoginRequiredMixin, View):
    '''用户中心-地址页'''
    def get(self,request):
        '''显示'''

        # 获取登录用户对应的User对象
        user = request.user

        # 获取用户的默认收获地址
        # try:
        #     # address里的user 等于 user里的user   address里的is_default=True的时候
        #     # 查到了默认收货地址
        #     # is_default==True就说明有默认收货地址
        #     address = Address.objects.get(user=user, is_default=True) # objects默认类型是models.Manager的对象
        # except Address.DoesNotExist:
        #     # 说明不存在默认收货地址
        #     address = None

        #　修改了模型管理器　可以去这个模型类里面看
        address = Address.objects.get_default_address(user)

        # 使用模板把address传递过去
        return render(request, 'user_center_site.html', {'page':'address', 'address':address})

    def post(self, request):
        ''' 地址的添加 '''
        # 接收数据
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')

        # 校验数据
        # 邮编可写可不写 模型类是这样定义的所以这里 不用判断它
        # 有数据为空时
        if not all([receiver, addr, phone]):
            return render(request, 'user_center_site.html', {'errmsg':'数据不完整'})

        # 校验手机号 是否为正常手机号
        if not re.match(r'^1[3|4|5|7|8][0-9]{9}$', phone):
            return render(request, 'user_center_site.html', {'errmsg':'手机格式不正确'})

        # 业务处理:地址添加
        # 如果用户已存在默认收货地址, 添加的地址不作为默认收货地址, 否则作为默认收货地址
        # 登录进来以后 request.user 是这个用户的对象
        # 获取登录用户对应的User对象
        user = request.user
        # try:
        #     # address里的user 等于 user里的user   address里的is_default=True的时候
        #     # 查到了默认收货地址
        #     # is_default==True就说明有默认收货地址
        #     address = Address.objects.get(user=user, is_default=True)
        # except Address.DoesNotExist:
        #     # 说明不存在默认收货地址
        #     address = None

        # 　修改了模型管理器　可以去这个模型类里面看
        address = Address.objects.get_default_address(user)

        # address!=None就是查到了这个用户有默认地址
        # is_default==False就不把它当做默认收货地址
        if address:
            is_default = False
        else:
        # is_default==True就把它当做收货地址
            is_default = True

        # 添加地址
        # create(意思是往address表里面加一条信息)
        Address.objects.create(user=user, receiver=receiver, addr=addr, zip_code=zip_code, phone=phone, is_default=is_default)

        # 返回应答,刷新地址页面
        return redirect(reverse('user:address')) # 重定向是get请求方式