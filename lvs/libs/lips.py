#-*- coding: utf-8 -*-

""" 根据 lb 的 ip 和 netmask 获取 lips(local ip).

"""


def _ipToInt(ip):
    ip_items = ip.split('.')

    ip_int = 0
    for item in ip_items:
        ip_int = ip_int * 256 + int(item)

    return ip_int


def _intToIp(ip_int):
    ip_items = ['0', '0', '0', '0']
    for i in range(0, 4):
        ip_items[3 - i] = str(ip_int % 256)
        ip_int = int((int(ip_int) - int(ip_items[3 - i])) / 256)

    seq = '.'
    ip = seq.join(ip_items)

    return ip


def _ipsm(ip, sm):
    ip_int = _ipToInt(ip)
    sm_int = _ipToInt(sm)

    total = 256 ** 4

    subnet_int = total - sm_int
    net_int = int(ip_int / subnet_int) * subnet_int

    neibor_ip = []
    for i in range(1, subnet_int - 1):
        neibor_int = net_int + i
        neibor_ip.append(_intToIp(neibor_int))
    return neibor_ip


def get(ip, netmask):
    iplist = _ipsm(ip, netmask)

    return iplist[2:]
