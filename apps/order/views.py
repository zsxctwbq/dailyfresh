from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.core.urlresolvers import reverse
from django.views.generic import View
from django_redis import get_redis_connection
# 导入操作数据库事务的包
from django.db import transaction
# 导入settings拼接应用秘钥 支付宝公钥的路径
from django.conf import settings
from goods.models import GoodsSKU
from user.models import Address
from order.models import OrderInfo, OrderGoods
from utils.mixin import LoginRequiredMixin
# 导入创建订单号的 时间模块
from datetime import datetime
# 导入与支付宝交互的包
from alipay import AliPay
import os

# /order/place
class OrderPlaceView(LoginRequiredMixin, View):
    '''提交订单页面显示'''
    def post(self, request):
        '''提交订单页面显示'''

        # 判断用户是否登入
        user = request.user

        # 接收数据
        sku_ids = request.POST.getlist('sku_ids')

        # 校验数据
        if not sku_ids:
            # 跳转到购物车页面
            return redirect(reverse('cart:show'))

        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id

        skus = []
        # 保存商品的总件数和总价格
        total_count = 0
        total_price = 0
        # 便利shu_ids获取用户要购买的商品信息
        for sku_id in sku_ids:
            try:
                sku = GoodsSKU.objects.get(id=sku_id)
                # 获取用户所要购买的商品的数量
                count = conn.hget(cart_key, sku_id)
                if count is None:
                    return redirect(reverse('goods:index'))
                # 计算商品的小计
                amount = sku.price*int(count)
                # 动态给sku增加属性count, 保存购买商品的数量
                sku.count = count
                # 动态给sku增加属性amount, 保存购买商品的小计
                sku.amount = amount
                # 追加
                skus.append(sku)
                # 累加
                total_count += int(count)
                total_price += amount

            except GoodsSKU.DoesNotExist:
                return redirect(reverse('cart:show'))

        # 运费:实际开发的时候, 属于一个子系统
        transit_price = 10 # 我们这里没做表 所以写死它

        # 实付款
        total_pay = total_price+transit_price


        # 获取用户的收件地址
        addrs = Address.objects.filter(user=user)


        # 组织上下文
        sku_ids = ','.join(sku_ids) # [1, 25]->1, 25
        context = {
            'skus':skus,
            'total_count':total_count,
            'total_price':total_price,
            'transit_price':transit_price,
            'total_pay':total_pay,
            'addrs':addrs,
            'sku_ids':sku_ids
        }

        # 使用模板
        return render(request, 'place_order.html', context)


# 创建订单
# 前端传递的参数:地址id(add_id) 支付方式(pay_method) 用户要购买的商品id字符串(sku_ids)
# mysql事务: 一组sql操作, 要么成功, 要么失败
# 高并发:秒杀
# 支付宝支付
# /order/commit
# todo: 在冲突比较少的时候,使用乐观锁(乐观锁重复操作的代价比较大时也用悲观锁), 在冲突比较多的时候用悲观锁
# 用的悲观锁(查询时加select_for_update()来上锁, 你拿到了, 别人就拿不打, 会被堵塞)
class OrderCommitView1(View):
    '''订单创建'''
    # todo: 饰了以后里面只要设计数据库的操作都是在一个事务里面
    # todo: 设计到的数据库操作 要么都成功, 要么都失败, 不允许(有成功的有失败的)
    @transaction.atomic
    def post(self, request):
        '''创建订单'''
        # 判断用户是否登入 这里用的ajax所以不能用我们提前写好的LoginRequiredMixin类
        user = request.user
        if not user.is_authenticated():
            # 用户没登入
            return JsonResponse({'res':0, 'errmsg':'请先登录'})
        # 接收数据
        # 地址id
        addr_id = request.POST.get('addr_id')
        # 支付方式
        pay_method = request.POST.get('pay_method')
        # 商品id
        sku_ids = request.POST.get('sku_ids')

        # 校验数据
        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res':1, 'errmsg':'数据不完整'})

        # 校验支付方式
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            # 支付方式非法
            return JsonResponse({'res':2, 'errmsg':'支付方式非法'})

        # 校验地址
        try:
            # 判断有没有这个地址的id
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res':3, 'errmsg':'地址非法'})


        # todo: 创建订单核心业务

        # 组织参数
        # 订单id:20190407230730+用户id
        order_id = datetime.now().strftime('%Y%m%d%H%M%S')+str(user.id)

        # 运费
        transit_price = 10

        # 总数目和总金额
        total_count = 0
        total_price = 0

        # todo: 设置事务保存点
        save_id = transaction.savepoint()

        try:
            # todo: 向df_order_info表中加入一条记录
            order = OrderInfo.objects.create(order_id=order_id,
                                             user=user,
                                             addr=addr,
                                             pay_method=pay_method,
                                             total_count=total_count,
                                             total_price=total_price,
                                             transit_price=transit_price)

            # todo: 用户的订单中有几个商品, 就需要向df_order_goods表中加入几条记录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%user.id

            # 把字符串转换成列表
            sku_ids = sku_ids.split(',')
            for sku_id in sku_ids:
                try:

                    # 获取商品的信息
                    # todo: mysql里面上锁是 select * from df_goods_sku where id=sku_id for update
                    # todo: 这里用的悲观锁(select_for_update是上锁, 别的进程运行到这的时候就会堵塞, 知道事务结束后别的进程才能拿的到锁)
                    sku = GoodsSKU.objects.select_for_update().get(id=sku_id)
                except GoodsSKU.DoesNotExist:
                    # todo: 因为商品不存在 所以要回滚到保存点(就是上面对数据库的操作无效, 因为对数据库的操作在保存点下面, 这只是mysql的回滚, 代码该往下走还是往下走的)
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse({'res':4, 'errmsg':'商品不存在'})

                # print('user_%d stock:%d'%(user.id, sku.stock))
                # import time
                # time.sleep(10)

                # 从redis中获取用户所要购买的商品的数量
                count = conn.hget(cart_key, sku_id)

                # todo: 判断商品的库存
                if int(count) > sku.stock:
                    # todo: 因为商品库存不存在 所以要回滚到保存点(就是上面对数据库的操作无效, 因为对数据库的操作在保存点下面, 这只是mysql的回滚, 代码该往下走还是往下走的)
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse({'res':5, 'errmsg':'库存不足'})

                # todo: 向df_order_goods表中添加一条记录
                OrderGoods.objects.create(order=order,
                                          sku=sku,
                                          count=count,
                                          price=sku.price)

                # todo: 订单建立完成,更新商品的销量和库存
                sku.stock -= int(count)
                sku.sales += int(count)
                # 更新到数据库
                sku.save()

                # todo: 累加计算订单商品的总金额和总数量
                amount = sku.price*int(count)
                total_count += int(count)
                total_price += amount

            # todo:更新订单信息表中的商品的总数量和总价格(df_order_info)
            order.total_count = total_count
            order.total_price = total_price
            # 跟新到数据库
            order.save()

        except Exception as e:
            # todo: 因为商品库存不存在 所以要回滚到保存点(就是上面对数据库的操作无效, 因为对数据库的操作在保存点下面, 这只是mysql的回滚, 代码该往下走还是往下走的)
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res':7, 'errmsg':'下单失败'})

        # todo: 如果对数据库的操作没有异常, 提交事务
        # todo: 把保存点到这里的所有sql语句提交
        transaction.savepoint_commit(save_id)

        # todo: 清除用户购物车中对应的记录(购物车要清理对应的商品)
        conn.hdel(cart_key, *sku_ids) # 把商品的id列表进行拆分
        # 返回应答
        return JsonResponse({'res':6, 'message':'创建成功'})

# 用的乐观锁(查询不需要上锁 在数据库跟新或者其他操作时做判断(我们所使用的数据有没有被改变,改变的话更新失败),(但是也不一定是库存不足所以循环)记住这里需要用的循环一般循环3次)
class OrderCommitView(View):
    '''订单创建'''
    # todo: 饰了以后里面只要设计数据库的操作都是在一个事务里面
    # todo: 设计到的数据库操作 要么都成功, 要么都失败, 不允许(有成功的有失败的)
    @transaction.atomic
    def post(self, request):
        '''创建订单'''
        # 判断用户是否登入 这里用的ajax所以不能用我们提前写好的LoginRequiredMixin类
        user = request.user
        if not user.is_authenticated():
            # 用户没登入
            return JsonResponse({'res':0, 'errmsg':'请先登录'})
        # 接收数据
        # 地址id
        addr_id = request.POST.get('addr_id')
        # 支付方式
        pay_method = request.POST.get('pay_method')
        # 商品id
        sku_ids = request.POST.get('sku_ids')

        # 校验数据
        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res':1, 'errmsg':'数据不完整'})

        # 校验支付方式
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            # 支付方式非法
            return JsonResponse({'res':2, 'errmsg':'支付方式非法'})

        # 校验地址
        try:
            # 判断有没有这个地址的id
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res':3, 'errmsg':'地址非法'})


        # todo: 创建订单核心业务

        # 组织参数
        # 订单id:20190407230730+用户id
        order_id = datetime.now().strftime('%Y%m%d%H%M%S')+str(user.id)

        # 运费
        transit_price = 10

        # 总数目和总金额
        total_count = 0
        total_price = 0

        # todo: 设置事务保存点
        save_id = transaction.savepoint()

        try:
            # todo: 向df_order_info表中加入一条记录
            order = OrderInfo.objects.create(order_id=order_id,
                                             user=user,
                                             addr=addr,
                                             pay_method=pay_method,
                                             total_count=total_count,
                                             total_price=total_price,
                                             transit_price=transit_price)

            # todo: 用户的订单中有几个商品, 就需要向df_order_goods表中加入几条记录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%user.id

            # 把字符串转换成列表
            sku_ids = sku_ids.split(',')
            for sku_id in sku_ids:
                for i in range(3):
                    try:
                        # 获取商品的信息
                        sku = GoodsSKU.objects.get(id=sku_id)
                    except GoodsSKU.DoesNotExist:
                        # todo: 因为商品不存在 所以要回滚到保存点(就是上面对数据库的操作无效, 因为对数据库的操作在保存点下面, 这只是mysql的回滚, 代码该往下走还是往下走的)
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res':4, 'errmsg':'商品不存在'})

                    # 从redis中获取用户所要购买的商品的数量
                    count = conn.hget(cart_key, sku_id)

                    # todo: 判断商品的库存
                    if int(count) > sku.stock:
                        # todo: 因为商品库存不存在 所以要回滚到保存点(就是上面对数据库的操作无效, 因为对数据库的操作在保存点下面, 这只是mysql的回滚, 代码该往下走还是往下走的)
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res':5, 'errmsg':'库存不足'})

                    # todo: 订单建立完成,更新商品的销量和库存(用乐观锁)
                    orgin_stock = sku.stock
                    new_stock = orgin_stock - int(count)
                    new_sales = sku.sales + int(count)

                    # print('user_%d %d stock:%d' % (user.id, i, sku.stock))
                    # import time
                    # time.sleep(10)

                    # todo: mysql语句应该这样update df_goods_sku set stock=new_stock, sales=new_sales where id=sku_id and stock = orgin_stock
                    # todo: 对应的代码, 返回受影响的行数
                    res = GoodsSKU.objects.filter(id=sku_id, stock=orgin_stock).update(stock=new_stock, sales=new_sales)
                    if res == 0:
                        # 返回0 就说明更新失败
                        if i == 2:
                            # 尝试的第三次
                            # todo: 所以要回滚到保存点(就是上面对数据库的操作无效, 因为对数据库的操作在保存点下面, 这只是mysql的回滚, 代码该往下走还是往下走的)
                            transaction.savepoint_rollback(save_id)
                            return JsonResponse({'res':7, 'errmsg':'下单失败2'})
                        continue

                    # todo: 向df_order_goods表中添加一条记录
                    OrderGoods.objects.create(order=order,
                                              sku=sku,
                                              count=count,
                                              price=sku.price)

                    # todo: 累加计算订单商品的总金额和总数量
                    amount = sku.price*int(count)
                    total_count += int(count)
                    total_price += amount

                    # 跳出循环
                    break

            # todo:更新订单信息表中的商品的总数量和总价格(df_order_info)
            order.total_count = total_count
            order.total_price = total_price
            # 跟新到数据库
            order.save()

        except Exception as e:
            # todo: 因为商品库存不存在 所以要回滚到保存点(就是上面对数据库的操作无效, 因为对数据库的操作在保存点下面, 这只是mysql的回滚, 代码该往下走还是往下走的)
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res':7, 'errmsg':'下单失败'})

        # todo: 如果对数据库的操作没有异常, 提交事务
        # todo: 把保存点到这里的所有sql语句提交
        transaction.savepoint_commit(save_id)

        # todo: 清除用户购物车中对应的记录(购物车要清理对应的商品)
        conn.hdel(cart_key, *sku_ids) # 把商品的id列表进行拆分
        # 返回应答
        return JsonResponse({'res':6, 'message':'创建成功'})


# ajax post
# 前端传递的参数: 订单id(order_id)
# /order/pay
class OrderPayView(View):
    '''订单支付'''
    def post(self, request):
        '''订单支付'''

        # 校验用户是否登入
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res':0, 'errmsg':'请先登入'})

        # 接收参数
        order_id = request.POST.get('order_id')
        # 校验参数
        if not order_id:
            return JsonResponse({'res':1, 'errmsg':'无效订单id'})

        try:
            # 订单id存不存在 是不是这个用户的订单 支付方式是不是支付宝 支付状态是不是待支付
            order = OrderInfo.objects.get(order_id=order_id, user=user, pay_method=3, order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res':2, 'errmsg':'订单错误'})

        # 业务处理:使用python SDK调用支付宝的支付接口
        # 初始化
        alipay = AliPay(
            appid="2016092500596768", # 使用支付宝沙箱的id(你有实际的id就用实际的)
            app_notify_url=None,  # 默认回调url
            app_private_key_path=os.path.join(settings.BASE_DIR, "apps/order/app_private_key.pem"), # 应用私钥路径
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_path=os.path.join(settings.BASE_DIR, "apps/order/alipay_public_key.pem"), # 支付宝公钥路径
            sign_type="RSA2", # RSA 或者 RSA2
            debug=True  # 默认False(这里用的沙箱所以是True 实际开发是False)
        )

        # 调用支付接口
        # 电脑网站支付，需要跳转到https://openapi.alipaydev.com/gateway.do? + order_string(这里是沙箱的地址 实际开发的地址alipay没有dev)
        total_pay = order.total_price + order.transit_price # Decimal类型是不能被转化成json的
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id, # 订单id
            total_amount=str(total_pay), # 支付总金额(这里用str 它内部自动将它转换成json)
            subject='天天生鲜%s'%order_id, # 订单标题
            return_url=None, # 我们这里没有公网的ip 所以填写了也接收不到所以(return_url, notify_url不填写, 但事后我们想知道用户付款没 可以去用支付宝提供的查询接口)
            notify_url=None  # 可选, 不填则使用默认notify url
        )

        # 返回应答
        pay_url = 'https://openapi.alipaydev.com/gateway.do?' + order_string
        return JsonResponse({'res':3, 'pay_url':pay_url})


# ajax post
# 前端传递的参数: 订单id(order_id)
# /order/check
class CheckPayView(View):
    '''查看订单支付的结果'''
    def post(self, request):
        # 判断用户是否登入
        user = request.user
        if not user.is_authenticated():
            print(1)
            return JsonResponse({'res':0, 'errmsg':'请先登录'})

        # 接收数据
        order_id = request.POST.get('order_id')

        # 校验数据
        if not order_id:
            print(2)
            return JsonResponse({'res':1, 'errmsg':'无效订单id'})

        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user, order_status=1, pay_method=3)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res':2, 'errmsg':'订单错误'})


        # 业务处理:使用python SDK调用支付宝的支付接口
        # 初始化
        alipay = AliPay(
            appid="2016092500596768",  # 使用支付宝沙箱的id(你有实际的id就用实际的)
            app_notify_url=None,  # 默认回调url
            app_private_key_path=os.path.join(settings.BASE_DIR, "apps/order/app_private_key.pem"),  # 应用私钥路径
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_path=os.path.join(settings.BASE_DIR, "apps/order/alipay_public_key.pem"),  # 支付宝公钥路径
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True  # 默认False(这里用的沙箱所以是True 实际开发是False)
        )

        # 调用支付宝的交易查询接口
        while True:
            response = alipay.api_alipay_trade_query(order_id)

            # 返回的response就是这样的一个字典
            # response = {
            #     "trade_no": "2017032121001004070200176844", # 支付宝交易号
            #     "code": "10000", # 接口调用是否成功
            #     "invoice_amount": "20.00",
            #     "open_id": "20880072506750308812798160715407",
            #     "fund_bill_list": [
            #       {
            #         "amount": "20.00",
            #         "fund_channel": "ALIPAYACCOUNT"
            #       }
            #     ],
            #     "buyer_logon_id": "csq***@sandbox.com",
            #     "send_pay_date": "2017-03-21 13:29:17",
            #     "receipt_amount": "20.00",
            #     "out_trade_no": "out_trade_no15",
            #     "buyer_pay_amount": "20.00",
            #     "buyer_user_id": "2088102169481075",
            #     "msg": "Success",
            #     "point_amount": "0.00",
            #     "trade_status": "TRADE_SUCCESS", # 支付结果
            #     "total_amount": "20.00"
            # }

            # response里的 code是10000(表示调用成功) 20000(表示不成功) 20001(授权权限不足) 40001(缺少必要的参数) 40002(非法参数)
            # 40004(业务处理失败) 40006(权限不足)

            # response里的 trade_status值为TRADE_SUCCESS（交易支付成功） WAIT_BUYER_PAY（交易创建，等待买家付款）、
            # TRADE_CLOSED（未付款交易超时关闭，或支付完成后全额退款）、TRADE_FINISHED（交易结束，不可退款）

            code = response.get('code')
            trade_status = response.get('trade_status')
            if code == '10000' and trade_status == 'TRADE_SUCCESS':
                # 支付成功
                # 获取支付宝交易号
                trade_no = response.get('trade_no')
                # 更新订单的状态
                order.trade_no = trade_no
                order.order_status = 4 # 待评价的状态
                order.save()
                # 返回结果
                return JsonResponse({'res':3, 'message':'支付成功'})
            elif code == '40004' or (code == '10000' and trade_status == 'WAIT_BUYER_PAY'):
                # 等待买家付款
                # 业务处理失败, 可能一会就会成功
                import time
                time.sleep(5)
                continue
            else:
                # 支付出错
                print(code)
                return JsonResponse({'res':4 , 'errmsg':'支付失败'})


class CommentView(LoginRequiredMixin, View):
    """订单评论"""
    def get(self, request, order_id):
        """提供评论页面"""
        user = request.user

        # 校验数据
        if not order_id:
            return redirect(reverse('user:order'))

        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse("user:order"))

        # 根据订单的状态获取订单的状态标题
        order.status_name = OrderInfo.ORDER_STATUS[order.order_status]

        # 获取订单商品信息
        # 因为订单里的每一个商品的order_id 都是订单的id
        order_skus = OrderGoods.objects.filter(order_id=order_id)
        for order_sku in order_skus:
            # 计算商品的小计
            amount = order_sku.count*order_sku.price
            # 动态给order_sku增加属性amount,保存商品小计
            order_sku.amount = amount
        # 动态给order增加属性order_skus, 保存订单商品信息
        order.order_skus = order_skus

        # 使用模板
        return render(request, "order_comment.html", {"order": order})

    def post(self, request, order_id):
        """处理评论内容"""
        user = request.user
        # 校验数据
        if not order_id:
            return redirect(reverse('user:order'))

        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse("user:order"))

        # 获取评论条数
        total_count = request.POST.get("total_count")
        total_count = int(total_count)

        # 循环获取订单中商品的评论内容
        # 这里的for循环用的很巧妙 根据商品的评论 循坏得出前端的商品id 和评论内容
        for i in range(1, total_count + 1):
            # 获取评论的商品的id
            sku_id = request.POST.get("sku_%d" % i) # sku_1 sku_2
            # 获取评论的商品的内容 没有的话返回一个空
            content = request.POST.get('content_%d' % i, '') # cotent_1 content_2 content_3
            try:
                order_goods = OrderGoods.objects.get(order=order, sku_id=sku_id)
            except OrderGoods.DoesNotExist:
                continue

            order_goods.comment = content
            order_goods.save()

        order.order_status = 5 # 已完成
        order.save()

        return redirect(reverse("user:order", kwargs={"page": 1}))




