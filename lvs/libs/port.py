#-*- coding: utf-8 -*-

""" 增加和删除 vip 的 port.

"""

import copy

from libs import log, redisoj
from lvs.libs import funcs
from web.const import REDIS_DB_LVS


logger = log.get_logger("LVS PORT")
_redis_oj = redisoj.PooledConnection(REDIS_DB_LVS)
client = _redis_oj.get()


def add(name, vip, ports):
    """ 对一个集群的一个 vip 增加若干个 port.

    ports 是一个 list, 格式如下:
    [
        {
            dport: xxx,
            synproxy: 1,
            sport: yyy,
            persistence_timeout: 50
        },
        {
            dport: aaa,
            synproxy: 0,
            sport: bbb,
            persistence_timeout: 50
        },
        ...    
    ]

    事实上如何鉴别多个 port 是否重复呢, 答案是根据 sport.

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
    old_vip2ws = eval(client.hget(key, "vip2ws"))

    # 检查 vip 是否存在.
    vips = [i["vip"] for i in old_vip2ws]
    if vip not in vips:
        logger.error("No vip:%s" % vip)
        return False

    # 增加 ports.
    vip2ws = list()
    for i in old_vip2ws:
        if i["vip"] == vip:
            old_sports = [x["sport"] for x in i["ports"]]
            new_sports = [x["sport"] for x in ports]
            if True in map(lambda x:x in old_sports, new_sports):
                logger.error("Sport duplicates:%s" % new_sports)
                return False

            i["ports"].extend(ports)
            vip2ws.append(i)
        else:
            vip2ws.append(i)

    # 保存集群信息.
    client.hset(key, "vip2ws", vip2ws)

    logger.info("Ports added:%s, %s" % (vip, ports))
    return True


def delete(name, vip, sports):
    """ 删除一个集群的一个 vip 的若干个端口.

    sports 是一个 list, 格式如下:
    [80, 443, ...]

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
    old_vip2ws = eval(client.hget(key, "vip2ws"))

    # 检查 vip 是否存在.
    vips = [i["vip"] for i in old_vip2ws]
    if vip not in vips:
        logger.error("No vip:%s" % vip)
        return False

    # 增加 ports.
    vip2ws = list()
    for i in old_vip2ws:
        if i["vip"] == vip:
            for j in i["ports"]:
                if j["sport"] in sports:
                    i["ports"].remove(j)
            vip2ws.append(i)
        else:
            vip2ws.append(i)

    # 保存集群信息.
    client.hset(key, "vip2ws", vip2ws)

    logger.info("Ports deleted:%s, %s" % (vip, sports))
    return True


def modify(name, vip, sport, port):
    """ 修改一个集群的一个 vip 的一个 port.

    sport 指明是哪个端口;
    port 是一个 dict, 格式如下:
    {
        dport: aaa,
        synproxy: 0,
        sport: bbb,
        persistence_timeout: 50
    }
    dict 中的 sport 可以不指定, 如果指定会修改成指定值;
    另外三个字段可以随意指定, 不指定的话不修改.

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
    old_vip2ws = eval(client.hget(key, "vip2ws"))

    # 检查 vip 是否存在.
    vips = [i["vip"] for i in old_vip2ws]
    if vip not in vips:
        logger.error("No vip:%s" % vip)
        return False

    # 增加 ports.
    vip2ws = list()
    for i in old_vip2ws:
        if i["vip"] == vip:
            for j in i["ports"]:
                if j["sport"] == sport:
                    _tmp = copy.deepcopy(j)
                    for _key in port:
                        _tmp[_key] = port[_key]
                    i["ports"].remove(j)
                    i["ports"].append(_tmp)
            vip2ws.append(i)
        else:
            vip2ws.append(i)

    # 保存集群信息.
    client.hset(key, "vip2ws", vip2ws)

    logger.info("Ports modified:%s, %s, %s" % (vip, sport, port))
    return True
