#-*- coding: utf-8 -*-

""" 增加和删除 lb.

"""

import copy

from libs import log, redisoj
from lvs.libs import funcs, lips
from web.const import REDIS_DB_LVS


logger = log.get_logger("LVS LB")
_redis_oj = redisoj.PooledConnection(REDIS_DB_LVS)
client = _redis_oj.get()


def add(name, new_lbinfos):
    """ 增加 lb.

    """
    # 检查集群是否存在.
    checkdict = {
        "name": name,
    }
    if not funcs.check(checkdict, check_exist=True):
        logger.error("No cluster:%s" % name)
        return False

    # 获取新增 lb.
    new_lbs = [i["hostname"] for i in new_lbinfos]
    if len(new_lbs) != len(set(new_lbs)):
        logger.error("Lb duplicates")
        return False

    # 检查新增 lb 是否已经存在.
    checkdict = {
        "lbs": new_lbs
    }
    if not funcs.check(checkdict, check_exist=False):
        logger.error("Some lbs exist")
        return False

    # 对所有 lb 安装 lvs fullnat.
    ret = funcs.lb_multi(new_lbs)
    fails = [ i for i in ret if not i["result"]]
    if fails != []:
        message = "Some lbs install failed:%s" % \
            ",".join(fails)
        logger.error(message)
        return False
    message = "All lbs install success:%s" % \
        ",".join(new_lbs)
    logger.info(message)

    # 获取已有集群信息.
    key = "cluster:%s" % name
    _type = client.hget(key, "type")
    old_lbinfos = eval(client.hget(key, "lbinfos"))
    device = client.hget(key, "device")

    # 获取新的 lbinfos.
    lbinfos = copy.deepcopy(old_lbinfos)
    lbinfos.extend(new_lbinfos)
    del old_lbinfos

    # 配置 lb.
    for lbinfo in new_lbinfos:
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
        ret = funcs.ip(lb, _type, device, internalip, \
            internalnetmask, internalgateway, extraip, \
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
    client.hset(key, "lbinfos", lbinfos)
    
    logger.info("Lbs added:%s" % ",".join(new_lbs)) 
    return True


def delete(name, del_lbs):
    """ 删除 lb.

    要删除的 lb 应该先下线, 这里只在数据库中删除.

    """
    # 检查是否重复.
    if len(del_lbs) != len(set(del_lbs)):
        logger.error("Lb duplicates")
        return False

    # 检查 lb 是否存在.
    checkdict = {
        "name": name,
        "lbs": del_lbs
    }
    if not funcs.check(checkdict, check_exist=True):
        logger.error("Cluster or some lbs not exist")
        return False

    # 获取集群信息.
    key = "cluster:%s" % name
    old_lbinfos = eval(client.hget(key, "lbinfos"))

    # 删除 lb.
    lbinfos = copy.deepcopy(old_lbinfos)
    for i in lbinfos:
        for j in del_lbs:
            if i["hostname"] == j:
                lbinfos.remove(i)
    client.hset(key, "lbinfos", lbinfos)

    logger.info("Lbs deleted:%s" % ",".join(del_lbs))
    return True
