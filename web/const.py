#-*- coding: utf-8 -*-


# 绑定 IP 和 端口.
BIND_IP = "0.0.0.0"
BIND_PORT = "8084"

# 日志路径.
LOG_DIR = "./logs/"
LOG_FILE = "lvs_cluster.log"


# REDIS 信息.
REDIS_HOST = ""
REDIS_PORT = 6379
REDIS_DB_LVS = "1"

# 安装 LVS FULLNAT 命令, 在 LVS 上执行. 
LVS_FULLNAT_CMD = """ sudo -i wdinst lvs_fullnat &>/tmp/.lvs_fullnat.log & """

# 本地 known hosts 路径.
LOCAL_SSH_KNOWN_HOSTS = "/home/op/.ssh/known_hosts"

# LVS 配置文件模板和 LVS 机器配置文件备份目录.
LVS_TEMPLATE_DIR = "lvs/template/"
LVS_CFG_TMP_DIR = "lvs_conf_tmp_dir/"
LB_CFG_BAK_DIR = "/root/keepalived_bak/"
