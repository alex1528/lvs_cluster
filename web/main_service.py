#!/usr/bin/env python
#-*- coding: utf-8 -*-


import socket
import sys
import os

import ujson as json

import tornado.ioloop
import tornado.web
import tornado.httpserver
import tornado.options
import tornado.auth
import tornado.web
import tornado.escape
import tornado.netutil

from web.const import BIND_IP
from web.const import BIND_PORT
from libs.ldapauth import Auth
from lvs.web import service as lvs_service


class Application(tornado.web.Application):

    def __init__(self):
        handlers = [
            (r"/api/v1/lvs/?", lvs_service.ClusterALLHandler),
            (r"/api/v1/lvs/sync/?", lvs_service.SyncHandler),         
            (r"/api/v1/lvs/vips/?", lvs_service.VipsHandler),
            (r"/api/v1/lvs/lbs/?", lvs_service.LbsHandler),
            (r"/api/v1/lvs/([^/]+)/?", lvs_service.ClusterHandler),
            (r"/api/v1/lvs/([^/]+)/vips/?", lvs_service.VipHandler),
            (r"/api/v1/lvs/([^/]+)/lbs/?", lvs_service.LbHandler),
            (r"/api/v1/lvs/([^/]+)/wss/?", lvs_service.WsHandler),
            (r"/api/v1/lvs/([^/]+)/ports/?", lvs_service.PortsHandler),
            (r"/api/v1/lvs/([^/]+)/wstype/?", lvs_service.WstypeHandler),
        ]

        settings = {
        }

        tornado.web.Application.__init__(self, handlers, **settings)


def main():
    application = Application()

    sockets = tornado.netutil.bind_sockets(
        BIND_PORT, address=BIND_IP, family=socket.AF_INET)
    tornado.process.fork_processes(0)

    http_server = tornado.httpserver.HTTPServer(application, xheaders=True)
    http_server.add_sockets(sockets)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
