#-*- coding: utf-8 -*-

""" 一些功能集合.

"""


import os
import time
from multiprocessing.dummy import Pool as ThreadPool

from web.const import (LOCAL_SSH_KNOWN_HOSTS, LVS_FULLNAT_CMD, 
    REDIS_DB_LVS)
from libs import dnsapi, log, mail, redisoj, utils
from lvs.libs import conf, info


logger = log.get_logger("LVS FUNCS")
_redis_oj = redisoj.PooledConnection(REDIS_DB_LVS)
client = _redis_oj.get()


def check(_dict, check_exist=True):
    """ 检查 name, vip 或 lb 是否已经存在.

    _dict 格式如下:
        {
            "name": name,
            "vips": vips,
            "lbs": lbs
        }

    当 check_exist 为 True 时, _dict 中的信息即使有一个不存在, 返回 False;
    当 check_exist 为 False 时, _dict 中的信息即使有一个存在, 返回 False;

    """
    for key in _dict:
        if key == "name":
            name = _dict[key]
            if check_exist and not client.keys("cluster:" + name):
                return False
            if not check_exist and client.keys("cluster:" + name):
                return False
        else:
            if key == "vips":
                for v in _dict[key]:
                    if check_exist and v not in info.vips():
                        return False
                    if not check_exist and v in info.vips():
                        return False
            elif key == "lbs":
                for v in _dict[key]:
                    if check_exist and v not in info.lbs():
                        return False
                    if not check_exist and v in info.lbs():
                        return False
    return True


def ip(lb, _type, device, internalip, internalnetmask, \
    internalgateway, extraip=None, extranetmask=None, \
    extragateway=None):
    """ 配置 lb 的 ip.

    """
    time.sleep(120)

    # 配置 IP.
    cmd = "sudo -i wdconfig lvsfullnat_ip"
    rc, so, se = utils.remote_cmd(lb, cmd)
    if rc != 0:
        logger.error("Cfg %s ip failed - %s" % (lb, se))
        return False

    cmd = "cd /tmp/post_config/lvsfullnat_ip_config "\
            "&& sudo sh lvsfullnat_ip_config.sh "\
            "%s %s %s %s %s %s %s %s "\
            "&>/tmp/.lvsfullnat_ip_config.log &" % (\
            _type, device, internalip, internalnetmask, \
            internalgateway, extraip, extranetmask, \
            extragateway)
    sshcmd = """ ssh -oConnectTimeout=3 -oStrictHostKeyChecking=no """\
                """op@%s "%s" & """ % (lb, cmd)
    os.system(sshcmd)
    logger.info("Cfg lb ip: %s" % lb)

    # 先获取当前的内网 IP.
    origin_internalip = utils.dns_resolv([lb])[0]

    # 内网 IP 被改了, 修改 DNS.
    ret = dnsapi.modify_wrapper(lb, internalip)
    if ret == "failed":
        message = "Change %s dns ip from %s to %s failed" % \
                    (lb, origin_internalip, internalip)
        logger.error(message)
        return False

    message = "Change %s dns ip from %s to %s success" %\
                (lb, origin_internalip, internalip)
    logger.info(message)
    return True


def lips(lb, ip, lips):
    """ 配置 lb 的 lips.

    """
    # 因为改了 DNS, 先清空本地 known_hosts 文件.
    cmd = "cat /dev/null >%s" % LOCAL_SSH_KNOWN_HOSTS
    rc, so, se = utils.shell(cmd)
    if rc != 0:
        message = "clean %s failed." % LOCAL_SSH_KNOWN_HOSTS
        logger.error(message)
        return False

    message = "Waiting for network administor to change "\
                "network conf for %s" % lb
    logger.info(message)

    # 发邮件让网络工程师修改 lb 的网络配置.
    subject = u"[接入集群]请在一小时之内修改%s的网络设置, 否则集群会建立失败" % lb
    context = ""
    mail.mail(None, subject, context)

    # 检查是否能够 ping 通.
    time.sleep(120)
    checkcmd = "ping -c 3 %s &>/dev/null" % ip
    ret = utils.check_wait_null(checkcmd, timeinit=0, \
        interval=5, timeout=3600)
    if not ret:
        logger.error("Ping failed, lb:%s, ip:%s" % (lb, ip))
        return False

    # 配置 lip.
    cmd = "sudo -i wdconfig lvsfullnat_lip"
    rc, so, se = utils.remote_cmd(ip, cmd)
    if rc != 0:
        message = "Cfg lips failed, lb:%s, error:%s" % (lb, se)
        logger.error(message)
        return False

    cmd = "cd /tmp/post_config/lvsfullnat_lip_config && "\
            "sudo sh lvsfullnat_lip_config.sh %s " % " ".join(lips)
    rc, so, se = utils.remote_cmd(ip, cmd)
    if rc != 0:
        message = "Cfg lips failed, lb:%s, error:%s" % (lb, se)
        logger.error(message)
        return False

    return True


def sync(name):
    """ 传输一个集群的配置到 lb.

    """
    key = "cluster:%s" % name
    _type = client.hget(key, "type")
    lbinfos = eval(client.hget(key, "lbinfos"))
    vip2ws = eval(client.hget(key, "vip2ws"))
    vipnets = eval(client.hget(key, "vipnets"))
    device = client.hget(key, "device")

    ret = conf.generate(_type, lbinfos, vip2ws, vipnets, device)
    if not ret:
        message = "Generate lb cfg failed:%s" % name
        logger.error(message)
        return False

    logger.error("Generate lb cfg success:%s" % name)
    return True


def _lb_single(host):
    """ 安装单台 lb.

    """    
    # 执行安装 fullnat 的命令.
    rc, so, se = utils.remote_cmd(host, LVS_FULLNAT_CMD)

    # 安装 lvs fullnat 完成后会重启系统, 当 ping 不通时,
    # 说明已经重启系统.
    checkcmd = "! ping -c 3 %s &>/dev/null" % host
    ret = utils.check_wait_null(
        checkcmd, timeinit=0, interval=5, timeout=2700)
    if not ret:
        return False

    # 当 ping 通时, 说明已经重启完毕.
    checkcmd = "ping -c 3 %s &>/dev/null" % host
    ret = utils.check_wait_null(
        checkcmd, timeinit=0, interval=5, timeout=1200)

    return {"host": host, "result": ret}


def lb_multi(hosts):
    """ 安装多台 lb.

    """
    pool = ThreadPool(10)
    results = pool.map(_lb_single, hosts)
    pool.close()
    pool.join()
    return results
