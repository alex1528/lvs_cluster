#-*- coding: utf-8 -*-

""" 获取, 增加和删除 cluster.

"""


import time

from libs import log, redisoj
from lvs.libs import funcs
from web.const import REDIS_DB_LVS


logger = log.get_logger("LVS CLUSTER")
_redis_oj = redisoj.PooledConnection(REDIS_DB_LVS)
client = _redis_oj.get()


def add(name, _type, lbinfos, vip2ws, vipnets, device):
    """ 增加一个 cluster.

    """
    # 拿到 lb 信息.
    lbs = [i["hostname"] for i in lbinfos]
    if len(lbs) != len(set(lbs)):
        logger.error("Lb duplicates")
        return False

    # 拿到 vip 信息.
    vips = [i["vip"] for i in vip2ws]
    if len(vips) != len(set(vips)):
        logger.error("Vip duplicates")
        return False

    # 检查 name, lb 和 vip 是否不存在.
    check_dict = {
        "name": name,
        "lbs": lbs,
        "vips": vips,
    }
    if not funcs.check(check_dict, check_exist=False):
        logger.error("Cluster or lbs or vips has exists.")
        return False

    # 对所有 lb 安装 lvs fullnat.
    ret = funcs.lb_multi(lbs)
    fails = [ i for i in ret if not i["result"]]
    if fails != []:
        message = "Some lbs install failed:%s" % \
            ",".join(fails)
        logger.error(message)
        return False
    else:
        message = "All lbs install success:%s" % \
            ",".join(lbs)
        logger.info(message)

    # 配置 lb.
    for lbinfo in lbinfos:
        lb = lbinfo["hostname"]
        internalip = lbinfo["internalip"]
        internalnetmask = lbinfo["internalnetmask"]
        internalgateway = lbinfo["internalgateway"]

        # 如果 _type 是 extra, 需要公网 IP;
        # 如果 _type 是 internal, 不需要公网 IP.
        extraip = lbinfo.get("extraip", None)
        extranetmask = lbinfo.get("extranetmask", None)
        extragateway = lbinfo.get("extragateway", None)

        # 配置 IP.
        ret = funcs.ip(lb, _type, device, internalip, 
                       internalnetmask, internalgateway, extraip, 
                       extranetmask, extragateway)
        if not ret:
            return False

        # 配置 lip.
        _lips = lips.get(internalip, internalnetmask)
        ret = funcs.lips(lb, internalip, _lips)
        if not ret:
            logger.error("Cfg lb lips failed:%s" % lb)
            return False
        logger.info("Cfg lb lips success:%s" % lb)

    # 保存集群信息.
    key = "cluster:%s" % name
    client.hset(key, "type", _type)
    client.hset(key, "lbinfos", lbinfos)
    client.hset(key, "vip2ws", vip2ws)
    client.hset(key, "vipnets", vipnets)
    client.hset(key, "device", device)

    logger.info("Cluster added:%s" % name)        
    return True


def delete(name):
    """ 删除一个集群.

    删除集群需要在集群完全不用之后, 只删除数据库信息.

    """
    # 检查集群是否存在.
    check_dict = {
        "name": name,
    }
    if not funcs.check(check_dict, check_exist=True):
        logger.error("No cluster:%s" % name)
        return False

    key = "cluster:%s" % name
    client.delete(key)

    logger.info("Cluster deleted:%s" % name)
    return True
