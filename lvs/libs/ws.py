#-*- coding: utf-8 -*-

""" 增加和删除 ws.

"""

import copy

from libs import log, redisoj
from lvs.libs import funcs 
from web.const import REDIS_DB_LVS


logger = log.get_logger("LVS WS")
_redis_oj = redisoj.PooledConnection(REDIS_DB_LVS)
client = _redis_oj.get()


def add(name, new_vip2ws):
    """ 增加 Ws.

    由于 ws 属于 vip,  所以需要传入 vip, 而且 vip 都要存在.

    new_vip2ws 只需要含有 vip 和 wss 两个 key 即可.

    """
    # 获取 vip.
    share_vips = [i["vip"] for i in new_vip2ws]
    if len(share_vips) != len(set(share_vips)):
        logger.error("Vip duplicates")
        return False

    # 检查是否 vip 是否存在.
    checkdict = {
        "name": name,
        "vips": share_vips
    }
    if not funcs.check(checkdict, check_exist=True):
        logger.error("Cluster or some vips not exist")
        return False

    # 获取集群信息.
    key = "cluster:%s" % name
    old_vip2ws = eval(client.hget(key, "vip2ws"))

    # 检查 vip 是否在集群中.
    vips = [i["vip"] for i in old_vip2ws]
    if True in map(lambda x:x not in vips, share_vips):
        logger.error("Some vips not exist")
        return False

    # 生成新的 vip2ws.
    vip2ws = list()
    for i in old_vip2ws:
        if i["vip"] in share_vips:
            for j in new_vip2ws:
                if i["vip"] == j["vip"]:
                    tmp = copy.deepcopy(i["wss"])
                    map(lambda x:tmp.append(x), j["wss"])
                    i["wss"] = list(set(tmp))
                    vip2ws.append(i)
        else:
            vip2ws.append(i)

    # 保存集群信息.
    client.hset(key, "vip2ws", vip2ws)

    logger.info("Wss added:%s" % new_vip2ws)
    return True


def delete(name, del_vip2ws):
    """ 删除 ws.

    由于 ws 属于 vip,  所以需要传入 vip, 而且 vip 都要存在.

    new_vip2ws 只需要含有 vip 和 wss 两个 key 即可.

    """
    # 获取 vip.
    share_vips = [i["vip"] for i in del_vip2ws]
    if len(share_vips) != len(set(share_vips)):
        logger.error("Vip duplicates")
        return False

    # 检查是否 vip 是否存在.
    checkdict = {
        "name": name,
        "vips": share_vips
    }
    if not funcs.check(checkdict, check_exist=True):
        logger.error("Cluster or some vips not exist")
        return False

    # 获取集群信息.
    key = "cluster:%s" % name
    old_vip2ws = eval(client.hget(key, "vip2ws"))

    # 获取新的 vip2ws.
    vip2ws = list()
    for i in old_vip2ws:
        if i["vip"] in share_vips:
            old_wss = copy.deepcopy(i["wss"])

            for j in del_vip2ws:
                if i["vip"] == j["vip"]:
                    break
            del_wss = copy.deepcopy(j["wss"])

            i["wss"] = list(set(old_wss) - set(del_wss))
            vip2ws.append(i)
        else:
            vip2ws.append(i)

    # 保存集群信息.
    client.hset(key, "vip2ws", vip2ws)

    logger.info("Wss deleted:%s" % del_vip2ws)
    return True
