#-*- coding: utf-8 -*-


import socket
import sys
import os

import ujson as json
import tornado.web

from libs import redisoj
from lvs.libs import funcs, info
from lvs.libs import cluster, vip, lb, ws, port, wstype
from web.const import REDIS_DB_LVS


_redis_oj = redisoj.PooledConnection(REDIS_DB_LVS)
client = _redis_oj.get()


def _self_write(status, name, module, func, cfg_push=False):
    """ 代码重用.

    """
    fail = {
        "status": "failed",
        "message": "%s %sed failed" % (module, func)
    }
    succ = {
        "status": "success",
        "message": "%s has been %sed successfully" % (module, func)
    }

    if not status:
        return fail

    if cfg_push not in [True, "True"]:
        return succ

    if funcs.sync(name):
        return succ
    else:
        return fail


class ClusterALLHandler(tornado.web.RequestHandler):

    def get(self):
        """ 查看所有集群信息. 

        """
        _ret = info.cluster(name=None)
        ret = {
            "status": "success",
            "message": _ret
        }
        self.write(json.dumps(ret))

    def post(self):
        """ 增加一个集群. 

        """
        name = self.get_argument("name")
        _type = self.get_argument("type")
        lbinfos = json.loads(self.get_argument("lbinfos"))
        vip2ws = json.loads(self.get_argument("vip2ws"))
        vipnets = json.loads(self.get_argument("vipnets"))
        device = self.get_argument("device")
        cfg_push = self.get_argument("cfg_push", True)

        status = cluster.add(name, _type, lbinfos, vip2ws, vipnets, device)
        ret = _self_write(status, name, "cluster", "add", cfg_push)
        self.write(json.dumps(ret))


class ClusterHandler(tornado.web.RequestHandler):

    def get(self, name):
        """ 查看一个集群信息.

        """
        _ret = info.cluster(name)
        ret = {
            "status": "success",
            "message": _ret
        }
        self.write(json.dumps(ret))

    def delete(self, name):
        """ 删除一个集群.

        """
        status = cluster.delete(name)
        ret = _self_write(status, name, "cluster", "delet")
        self.write(json.dumps(ret))


class VipHandler(tornado.web.RequestHandler):

    def post(self, name):
        """ 增加一个 VIP.

        """
        vip2ws = json.loads(self.get_argument("vip2ws"))
        cfg_push = self.get_argument("cfg_push", True)

        status = vip.add(name, vip2ws)
        ret = _self_write(status, name, "vip", "add", cfg_push)
        self.write(json.dumps(ret))

    def delete(self, name):
        """ 删除 VIP.

        """
        vips = json.loads(self.get_argument("vips"))
        cfg_push = self.get_argument("cfg_push", True)

        status = vip.delete(name, vips)
        ret = _self_write(status, name, "vip", "delet", cfg_push)
        self.write(json.dumps(ret))


class LbHandler(tornado.web.RequestHandler):

    def post(self, name):
        """ 增加一个 Lb.

        """
        lbinfos = json.loads(self.get_argument("lbinfos"))
        cfg_push = self.get_argument("cfg_push", True)

        status = lb.add(name, lbinfos)
        ret = _self_write(status, name, "lb", "add", cfg_push)
        self.write(json.dumps(ret))

    def delete(self, name):
        """ 删除 Lb.

        """
        lbs = json.loads(self.get_argument("lbs"))
        cfg_push = self.get_argument("cfg_push", True)

        status = lb.delete(name, lbs)
        ret = _self_write(status, name, "lb", "delet", cfg_push)
        self.write(json.dumps(ret))


class WsHandler(tornado.web.RequestHandler):

    def post(self, name):
        """ 增加一个 Ws.

        """
        vip2ws = json.loads(self.get_argument("vip2ws"))
        cfg_push = self.get_argument("cfg_push", True)

        status = ws.add(name, vip2ws)
        ret = _self_write(status, name, "ws", "add", cfg_push)
        self.write(json.dumps(ret))

    def delete(self, name):
        """ 删除 Ws.

        """
        vip2ws = self.get_argument("vip2ws")
        vip2ws = json.loads(vip2ws)
        cfg_push = self.get_argument("cfg_push", True)

        status = ws.delete(name, vip2ws)
        ret = _self_write(status, name, "ws", "delet", cfg_push)
        self.write(json.dumps(ret))


class PortsHandler(tornado.web.RequestHandler):

    def post(self, name):
        """ 增加若干个 port.

        """
        vip = self.get_argument("vip")
        ports = json.loads(self.get_argument("ports"))
        cfg_push = self.get_argument("cfg_push", True)

        status = port.add(name, vip, ports)
        ret = _self_write(status, name, "port", "add", cfg_push)
        self.write(json.dumps(ret))

    def delete(self, name):
        """ 删除若干个 ports.

        """
        vip = self.get_argument("vip")
        sports = json.loads(self.get_argument("sports"))
        cfg_push = self.get_argument("cfg_push", True)

        status = port.delete(name, vip, sports)
        ret = _self_write(status, name, "port", "delet", cfg_push)
        self.write(json.dumps(ret))

    def patch(self, name):
        """ 修改 ports.

        """
        vip = self.get_argument("vip")
        sport = json.loads(self.get_argument("sport"))
        _port = json.loads(self.get_argument("port"))
        cfg_push = self.get_argument("cfg_push", True)

        status = port.modify(name, vip, sport, _port)
        ret = _self_write(status, name, "port", "modifi", cfg_push)
        self.write(json.dumps(ret))


class WstypeHandler(tornado.web.RequestHandler):

    def patch(self, name):
        """ 修改 wstype.

        """
        vip = self.get_argument("vip")
        _wstype = self.get_argument("wstype")
        cfg_push = self.get_argument("cfg_push", True)

        status = wstype.modify(name, vip, _wstype)
        ret = _self_write(status, name, "wstype", "modifi", cfg_push)
        self.write(json.dumps(ret))


class SyncHandler(tornado.web.RequestHandler):

    def post(self):
        """ 把一个集群的配置 sync 到线上.

        """
        name = self.get_argument("name")
        ret = _self_write(True, name, "cluster", "sync", True)
        self.write(json.dumps(ret))


class VipsHandler(tornado.web.RequestHandler):

    def get(self):
        """ 查看 vip 列表.

        """
        self.write(json.dumps(info.vips()))


class LbsHandler(tornado.web.RequestHandler):

    def get(self):
        """ 查看 lb 列表.

        """
        self.write(json.dumps(info.lbs()))
