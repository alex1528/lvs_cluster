#-*- coding: utf-8 -*-

""" 生成 LVS 配置文件并传输到 LVS 机器.

"""

import os
import time

from jinja2 import Environment, FileSystemLoader

from libs import log, utils
from lvs.libs import lips
from web.const import (LVS_TEMPLATE_DIR, LVS_CFG_TMP_DIR, 
                       LB_CFG_BAK_DIR)


logger = log.get_logger("LVS CONF")

if not os.path.exists(LVS_CFG_TMP_DIR):
    os.mkdir(LVS_CFG_TMP_DIR)


def _backup(hosts, remote_dir, base_dir=LB_CFG_BAK_DIR):
    """ 备份远程主机的目录. 

    """
    # 自定义
    now = time.strftime("%Y%m%d%H%I%M%S")
    bak_dir = "%s/%s_%s" % (base_dir, \
        remote_dir.replace("/","-"), now)

    for host in hosts:
        # 如果远程目录不存在, 就不备份.
        cmd = "test -d %s" % remote_dir
        rc, so, se = utils.remote_cmd(host, cmd)
        if rc != 0:
            continue

        # 备份基目录如果不存在, 创建.
        cmd = "sudo test -d %s ||sudo /bin/mkdir -p %s" % (
            base_dir, base_dir)
        utils.remote_cmd(host, cmd)

        # 执行备份.
        cmd = "sudo /bin/cp -a %s %s " % (remote_dir, bak_dir)
        rc, so, se = utils.remote_cmd(host, cmd)
        if rc != 0:
            return (False, se)

    return (True, None)


def generate(_type, lbinfos, vip2ws, vipnets, device):
    """ 生成和传输 keepalived 配置.

    """
    j2_env = Environment(loader=FileSystemLoader(LVS_TEMPLATE_DIR),
                         trim_blocks=True)

    # 各个模板文件名.
    keepalived_template = "keepalived.conf"
    sub_keepalived_template = "sub_keepalived.conf"
    zebra_template = "zebra.conf"
    ospfd_template = "ospfd.conf"

    # 建立存放 lvs 临时配置文件基目录.
    # lb 的配置文件分别几个部分, 一个是 keepalived.conf 主配置
    # 文件, 这个文件需要引用每个 VIP 的配置, 额外还需要 ospfd.conf
    # 和 zebra.conf 配置. 对于 VIP 配置, 所有 lb 都是一样的, 
    # keepalived.conf 主配置文件、 ospfd.conf 和 zebra.conf
    # 则每个 lb 都不一样.
    # 基目录下目录结构这么存放:
    # lbcommon 里面存 每个 lb 都一样的 VIP 配置;
    # 对于 每个 lb 建立一个目录, 下面有两个子目录, 分别是:
    # keepalived 和 ospfd, keepalived 下面是 keepalived.conf,
    # ospfd 下面是 ospfd.conf 和 zebra.conf.
    # 比如:
    #   ./lbcommon/xxx.xxx.xxx.xxx.conf
    #   ./$lb/ospfd/ospfd.conf
    #   ./$lb/ospfd/zebra.conf
    #   ./$lb/keepalived/keepalived.conf
    now = time.strftime("%Y%m%d%H%I%M%S")
    base_dir = LVS_CFG_TMP_DIR + "/" + now
    os.mkdir(base_dir)

    # 拿到 lb 和 vip.
    lbs = [i["hostname"] for i in lbinfos]
    vips = [i["vip"] for i in vip2ws]

    try:
        for lbinfo in lbinfos:
            lb = lbinfo["hostname"]
            internalip = lbinfo["internalip"]
            internalnetmask = lbinfo["internalnetmask"]
            internalgateway = lbinfo["internalgateway"]
            routerid = lbinfo["routerid"]
            ospfnet = lbinfo["ospfnet"]

            if _type == "extra":
                extraip = lbinfo["extraip"]
                extranetmask = lbinfo["extranetmask"]
                extragateway = lbinfo["extragateway"]

            _lips = lips.get(internalip, internalnetmask)

            # 对每个 lb 创建临时目录.
            lb_dir = base_dir + "/" + lb
            lb_keepalived_dir = lb_dir + "/keepalived"
            lb_osfpd_dir = lb_dir + "/ospfd"
            os.mkdir(lb_dir)
            os.mkdir(lb_keepalived_dir)
            os.mkdir(lb_osfpd_dir)

            # 对于 lb 生成配置.
            with open(lb_keepalived_dir + "/keepalived.conf", 'w') as f:
                f.writelines(
                    j2_env.get_template(keepalived_template).render(
                        lips=_lips, vips=vips, lb=lb.split(".")[0]
                    )                    
                )
            with open(lb_osfpd_dir + "/zebra.conf", 'w') as f:
                f.writelines(
                    j2_env.get_template(zebra_template).render(
                        lb=lb
                    )                    
                )
            with open(lb_osfpd_dir + "/ospfd.conf", 'w') as f:
                f.writelines(
                    j2_env.get_template(ospfd_template).render(
                        lb=lb, routerid=routerid, device=device, 
                        ospfnet=ospfnet, vipnets=vipnets
                    )                    
                )

        # 创建公共临时目录.
        lb_common_dir = base_dir + "/lbcommon"
        os.mkdir(lb_common_dir)

        # 获取 ports 和 wss.
        for vip in vips:
            for i in vip2ws:
                if vip == i["vip"]:
                    if "ports" not in i:
                        ports = [
                            {"sport": 80,
                             "dport": 80,
                             "synproxy": 1,
                             "persistence_timeout": 50
                             },
                            {"sport": 443,
                             "dport": 443,
                             "synproxy": 1,
                             "persistence_timeout": 50
                             }
                        ]
                    else:
                        ports = list()
                        for j in i["ports"]:
                            if "synproxy" not in j:
                                j["synproxy"] = 1
                            elif "persistence_timeout" not in j:
                                j["persistence_timeout"] = 50
                            ports.append(j)
                    wss = i["wss"]
                    break

            # 把 wss 解析成 IP.
            wss_ip = utils.dns_resolv(wss)
            if not wss_ip:
                message = "Some ws dns resolv failed, wss:%s" % wss
                logger.error(message)
                return False

            # 生成公共的 VIP 配置.
            with open(lb_common_dir + "/" + vip + ".conf", 'w') as f:
                f.writelines(
                    j2_env.get_template(sub_keepalived_template).render(
                        vip=vip, ports=ports, wss=wss_ip
                    )
                )

        message = "Make keepalived cfg success"
        logger.info(message)
    except Exception, e:
        message = "Make keepalived cfg failed:%s" % e
        logger.error(message)
        return False

    # 备份 lb 的配置文件.
    for dir in "/etc/keepalived/", "/usr/local/etc/":
        status, message = _backup(lbs, dir)
        if not status:
            logger.error(message)
            return False
    message = "Backup cfg success, lbs:" % lbs
    logger.info(message)

    # 删除 lb 的配置文件.
    for dir in "/etc/keepalived/", "/usr/local/etc/":
        cmd = "sudo /bin/rm -rf %s/*" % dir
        for lb in lbs:
            rc, so, se = utils.remote_cmd(lb, cmd)
            if rc != 0:
                logger.error(se)
                return False
    message = "Delete cfg success, lbs:%s" % lbs
    logger.info(message)

    # 传输配置.
    for lb in lbs:
        lb_dir = base_dir + "/" + lb
        lb_keepalived_dir = lb_dir + "/keepalived"
        lb_osfpd_dir = lb_dir + "/ospfd"

        _dict = {
            lb_keepalived_dir: "/etc/keepalived/",
            lb_osfpd_dir: "/usr/local/etc/",
            lb_common_dir: "/etc/keepalived/"   # 公共配置.
        }
        for i in _dict:
            local_dir = i
            remote_dir = _dict[i]
            ret = utils.transfer_dir([lb], local_dir, remote_dir)
            if not ret:
                message = "Transfer keepalived cfg failed, "\
                    "lb:%s, local_dir:%s, remote_dir:%s" % (
                    lb, local_dir, remote_dir)
                logger.error(message)
                return False
    message = "Transfer cfg success, lbs:%s" % lbs
    logger.info(message)
    return True
