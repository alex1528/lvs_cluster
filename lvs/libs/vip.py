#-*- coding: utf-8 -*-

""" 增加和删除 vip.

"""

import copy

from libs import log, redisoj
from lvs.libs import funcs 
from web.const import REDIS_DB_LVS


logger = log.get_logger("LVS VIP")
_redis_oj = redisoj.PooledConnection(REDIS_DB_LVS)
client = _redis_oj.get()


def add(name, new_vip2ws):
    """ 增加 VIP.

    """
    # 检查集群是否存在.
    checkdict = {
        "name": name,
    }
    if not funcs.check(checkdict, check_exist=True):
        logger.error("No cluster:%s" % name)
        return False

    # 获取新增 vip.
    new_vips = [i["vip"] for i in new_vip2ws]
    if len(new_vips) != len(set(new_vips)):
        logger.error("Vip duplicates")
        return False

    # 检查新增 vip 是否存在.
    checkdict = {
        "vips": new_vips,
    }
    if not funcs.check(checkdict, check_exist=False):
        logger.error("Some vips exist")
        return False

    # 获取集群信息.
    key = "cluster:%s" % name
    old_vip2ws = eval(client.hget(key, "vip2ws"))

    # 获取新的 vip2ws.
    vip2ws = copy.deepcopy(old_vip2ws)
    vip2ws.extend(new_vip2ws)
    del old_vip2ws

    # 保存集群信息.
    client.hset(key, "vip2ws", vip2ws)

    logger.info("Vips added:%s" % new_vip2ws)
    return True


def delete(name, del_vips):
    """ 删除 vip.

    """
    # 检查是否重复.
    if len(del_vips) != len(set(del_vips)):
        logger.error("Vip duplicates")
        return False

    # 检查是否存在.
    checkdict = {
        "name": name,
        "vips": del_vips
    }
    if not funcs.check(checkdict, check_exist=True):
        logger.error("Cluster or some vips not exist")
        return False

    # 获取集群信息.
    key = "cluster:%s" % name
    old_vip2ws = eval(client.hget(key, "vip2ws"))

    # 获取新的 vip2ws.
    vip2ws = copy.deepcopy(old_vip2ws)
    for i in vip2ws:
        for j in del_vips:
            if i["vip"] == j:
                vip2ws.remove(i)

    # 保存集群信息.
    client.hset(key, "vip2ws", vip2ws)

    logger.info("Vips deleted:%s" % ",".join(del_vips))
    return True
