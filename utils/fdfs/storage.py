# 导入自定义文件存储系统的包
from django.core.files.storage import Storage
# 导入python与fdfs文件存储系统的交互包
from fdfs_client.client import Fdfs_client
from django.conf import settings

class FDFSStorage(Storage):
    '''fast dfs文件存储类'''

    def __init__(self, client_conf=None, base_url=None):
        '''初始化'''
        if client_conf is None:
            # FDFS_CLIENT_CONF(我们把文件的配置 设置在settings里面去了 这样以后只需要在settings修改即可)
            client_conf = settings.FDFS_CLIENT_CONF
        # 文件配置
        self.client_conf = client_conf

        if base_url is None:
            # FDFS_URL(我们把文件的配置 设置在settings里面去了 这样以后只需要在settings修改即可)
            base_url = settings.FDFS_URL
        # 文件路径
        self.base_url = base_url


    def _open(self, name, mode='rb'):
        '''打开文件时使用'''
        pass

    # 当admin管理员点击保存时:django会调用Storage类里面的
    # save()方法这个方法内部会调用_save(他会给他传两个参数:
    # 1一个你要上传文件的名字, 一个是包含你要上传文件的File对象)
    def _save(self, name, content):
        '''保存文件时使用'''
        # name:你选择的上传文件的名字
        # content:包含你上传文件内容的File对象

        # 创建一个Fdfs_client对象 做上传使用
        # 写上你的配置文件路径
        clien = Fdfs_client(self.client_conf)

        # 上传文件到fast dfs系统中
        # content.read()获取你上传文件的内容
        # upload_by_buffer根据内容上传文件
        # res 返回回来的是一个字典
        res = clien.upload_by_buffer(content.read())

        # res 返回回来的格式
        # dict
        # {
        #     'Group name': group_name,
        #     'Remote file_id': remote_file_id,
        #     'Status': 'Upload successed.',
        #     'Local file name': '',
        #     'Uploaded size': upload_size,
        #     'Storage IP': storage_ip
        # }

        # 判断上传成功没
        if res.get('Status') != 'Upload successed.':
            # 上传失败
            # raise显示地引发异常。一旦执行了raise语句，raise后面的语句将不能执行
            raise Exception('上传文件到fast dfs失败')

        # 获取返回的文件id
        filename = res.get('Remote file_id')

        # 返回文件的id
        return filename

    # django调用save方法之前 他会调用exists方法这个文件在我本地有没有, 因为我们没有在本地存储这个文件所以,我们这里直接返回False
    def exists(self, name):
        '''django判断文件名是否可用'''
        # 返回True不可用 返回False可用
        return False

    # 列(页面上直接写GoodsSKU对象点image只会显示图片的id, 但是在页面上写GoodsSKU对象点image.url的时候就会调用这个方法,
    # 拼接出完整的路径, 找到图片借助了nginx, 可以去看nginx的配置)
    def url(self, name):
        '''返回访问url路径'''
        # 这个路径会返回到admin后台的目前下
        return self.base_url+name