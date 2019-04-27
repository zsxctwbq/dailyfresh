# 导入发邮件的包
from django.core.mail import send_mail
# 使用celery
from django.conf import settings
# 导入操作模板的 loader传模板进去得到模板对象
# RequestContext构造上下文
from django.template import loader
from celery import Celery
import time

# 在任务处理者一端加这些代码
# 完成django环境的初始化
import os
import django
# 设置环境变量的初始化 要不然异步时报错
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dailyfresh.settings")
# django初始化
django.setup()
# 启动celery-worker的时候这几个类的导入必须放在上面那4句的下面 不放在这下面celery-worker会报错说找不到这几个类
from goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner


# 创建一个Celery实例对象
# 一般里面的字符串就写这个
# 写上redis数据库的ip端口和使用的那个数据库 记住写上任务端的ip和端口 在数据库里面配置
# 这里对应的是redis8好数据库 让他做任务队列(中间人)
# 这就是celery配置
app = Celery('celery_tasks.tasks', broker='redis://172.16.66.228:6379/8')

# 定义任务函数
@app.task
def send_register_active_email(to_email, username, token):
    ''' 发送激活邮件 '''

    # 组织邮件信息
    # 标题
    subject = '天天生鲜欢饮信息'
    # 邮件的正文
    message = ''
    # 发件人
    sender = settings.EMAIL_FROM
    # 收件人列表
    receiver = [to_email]
    # 把你写的html标签 在邮件里面渲染
    html_message = '<h1>%s, 欢迎您成为天天生鲜注册会员</h1>请点击下面链接激活您的账户<br/><a href="http://172.16.66.228:8000/user/active/%s">http://172.16.66.228:8000/user/active/%s</a>' % (
    username, token, token)
    # 发送邮件
    # 这些参数都是一一对应的
    # 记住html_message放在最后等于你写的html
    send_mail(subject, message, sender, receiver, html_message=html_message)
    time.sleep(5)

@app.task
def generate_static_index_html():
    '''产生首页静态页面'''
    # 获取商品的种类信息
    types = GoodsType.objects.all()

    # 获取首页轮播商品信息
    # order_by排序 根据index排序
    goods_banners = IndexGoodsBanner.objects.all().order_by('index')  # 升序 0,1,2,3 要降序在index前面加个减号

    # 获取首页促销活动信息
    promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

    # 获取首页分类商品展示信息
    for type in types:  # 每一个对象都是GoodsType
        # 查询这个表里面type=type 并且 display_type=1的 order_by用index升序排序
        # (利用外键)
        # 获取type种类首页分类商品的图片展示信息
        image_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')

        # 获取type种类首页分类商品的文字展示信息
        title_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')

        # 动态给type增加属性, 分别保存首页分类商品的图片展示信息和文字展示信息
        type.image_banners = image_banners
        type.title_banners = title_banners

    # 组织模板上下文
    context = {'types': types,
               'goods_banners': goods_banners,
               'promotion_banners': promotion_banners
               }

    # 使用模板
    # 1.加载模板文件, 返回模板对象
    temp = loader.get_template('static_index.html')
    # 2.模板渲染
    # 用我传给它的字典来替换static_index.html 然后返回替换后的页面
    static_index_html = temp.render(context)

    # 生成首页对应静态文件
    save_path = os.path.join(settings.BASE_DIR, 'static/index.html')
    # 把这个路径下的这个未见用写打开
    with open(save_path, 'w') as f:
        # 把static_index_html写入进去
        f.write(static_index_html)