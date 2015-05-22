#-*- coding: utf-8 -*-

""" 获取 cluster, lb 和 vip 信息.

"""


import time

from libs import redisoj
from web.const import REDIS_DB_LVS


_redis_oj = redisoj.PooledConnection(REDIS_DB_LVS)
client = _redis_oj.get()


def cluster(name=None):
    """ 查询 cluster 信息.

    如果 name 为 None, 返回所有 cluster 信息.

    """
    if name is not None:
        key = "cluster:%s" % name
        _type = client.hget(key, "type")
        lbinfos = eval(client.hget(key, "lbinfos"))
        vip2ws = eval(client.hget(key, "vip2ws"))
        vipnets = eval(client.hget(key, "vipnets"))
        device = client.hget(key, "device")

        _cluster = {
            "name": name,
            "type": _type,
            "lbinfos": lbinfos,
            "vip2ws": vip2ws,
            "vipnets": vipnets,
            "device": device
        }
        return _cluster
    else:
        clusters = list()
        for key in client.keys("cluster:*"):
            name = key.split(":")[-1]
            _type = client.hget(key, "type")
            lbinfos = eval(client.hget(key, "lbinfos"))
            vip2ws = eval(client.hget(key, "vip2ws"))
            vipnets = eval(client.hget(key, "vipnets"))
            device = client.hget(key, "device")

            _cluster = {
                "name": name,
                "type": _type,
                "lbinfos": lbinfos,
                "vip2ws": vip2ws,
                "vipnets": vipnets,
                "device": device
             }
            clusters.append(_cluster)
        return clusters


def lbs():
    """ 获取所有 lb.

    """
    _lbs = list()
    ret = cluster(name=None)
    for i in ret:
        _lbs.extend([x["hostname"] for x in i["lbinfos"]])
    return _lbs


def vips():
    """ 获取所有 vip.

    """
    _vips = list()
    ret = cluster(name=None)
    for i in ret:
        _vips.extend([x["vip"] for x in i["vip2ws"]])
    return _vips
