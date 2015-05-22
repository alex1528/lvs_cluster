#-*- coding: utf-8 -*-

""" 修改 vip 的 wstype.

"""

import copy

from libs import log, redisoj
from lvs.libs import funcs
from web.const import REDIS_DB_LVS


logger = log.get_logger("LVS WSTYPE")
_redis_oj = redisoj.PooledConnection(REDIS_DB_LVS)
client = _redis_oj.get()


def modify(name, vip, wstype):
    """ 修改一个集群的一个 vip 的 wstype.

    """
    # 检查集群是否存在.
    check_dict = {
        "name": name,
    }
    if not funcs.check(check_dict, check_exist=True):
        logger.error("No cluster:%s" % name)
        return False

    # 获取集群信息.
    key = "cluster:%s" % name
    _type = client.hget(key, "type")
    lbinfos = eval(client.hget(key, "lbinfos"))
    old_vip2ws = eval(client.hget(key, "vip2ws"))
    vipnets = eval(client.hget(key, "vipnets"))
    device = client.hget(key, "device")

    # 检查 vip 是否存在.
    vips = [i["vip"] for i in old_vip2ws]
    if vip not in vips:
        logger.error("No vip:%s" % vip)
        return False        

    # 修改 wstype.
    vip2ws = list()
    for i in old_vip2ws:
        if i["vip"] == vip:
            i["wstype"] = wstype
            vip2ws.append(i)
        else:
            vip2ws.append(i)

    # 保存集群信息.
    client.hset(key, "vip2ws", vip2ws)

    logger.info("Wstype modified:%s, %s" % (vip, wstype))
    return True
