#!/usr/bin/env python
# encoding: utf-8
import os
import sys
import argparse
from zstacklib import *

start_time = datetime.now()
# set default value
file_root = "files/cephp"
pip_url = "https=//pypi.python.org/simple/"
proxy = ""
sproxy = ""
yum_repo = 'false'
post_url = ""

# get paramter from shell
parser = argparse.ArgumentParser(description='Deploy ceph backup strorage to host')
parser.add_argument('-i',type=str, help="""specify inventory host file
                        default=/etc/ansible/hosts""")
parser.add_argument('--private-key',type=str,help='use this file to authenticate the connection')
parser.add_argument('-e',type=str, help='set additional variables as key=value or YAML/JSON')

args = parser.parse_args()
argument_dict = eval(args.e)

# update the variable from shell arguments
locals().update(argument_dict)
virtenv_path = "%s/virtualenv/cephp/" % zstack_root
cephp_root = "%s/cephp" % zstack_root
host_post_info = HostPostInfo()
host_post_info.host_inventory = args.i
host_post_info.host = host
host_post_info.post_url = post_url
host_post_info.private_key = args.private_key

# include zstacklib.py
(distro, distro_version) = get_remote_host_info(host_post_info)
zstacklib_args = ZstackLibArgs()
zstacklib_args.distro = distro
zstacklib_args.distro_version = distro_version
zstacklib_args.yum_repo = yum_repo
zstacklib_args.yum_server = yum_server
zstacklib_args.zstack_root = zstack_root
zstacklib_args.host_post_info = host_post_info
zstacklib = ZstackLib(zstacklib_args)


# name: create root directories
command = 'mkdir -p %s %s' % (cephp_root,virtenv_path)
run_remote_command(command, host_post_info)
if distro == "RedHat" or distro == "CentOS":
    if yum_repo != 'false':
        command = "yum --disablerepo=* --enablerepo=%s --nogpgcheck install -y wget qemu-img" % yum_repo
        run_remote_command(command, host_post_info)
        if distro_version >= 7 :
            command = "rpm -q iptables-services || yum --disablerepo=* --enablerepo=%s --nogpgcheck install -y iptables-services " % yum_repo
            run_remote_command(command, host_post_info)
            command = "(which firewalld && service firewalld stop && chkconfig firewalld off) || true"
            run_remote_command(command, host_post_info)
    else:
        for pkg in ["wget","qemu-img"]:
            yum_install_package(pkg, host_post_info)
        if distro_version >= 7 :
            command = "rpm -q iptables-services || yum --nogpgcheck install -y iptables-services "
            run_remote_command(command, host_post_info)
            command = "(which firewalld && service firewalld stop && chkconfig firewalld off) || true"
            run_remote_command(command, host_post_info)
    set_selinux("state=permissive policy=targeted", host_post_info)

elif distro == "Debian" or distro == "Ubuntu":
    for pkg in ["wget","qemu-utils"]:
        apt_install_packages(pkg, host_post_info)
else:
    print "unsupported OS!"
    sys.exit(1)

check_and_install_virtual_env("12.1.1", trusted_host, pip_url, host_post_info)
# name: create virtualenv
command = "rm -rf %s && rm -f %s/%s && rm -f %s/%s && virtualenv --system-site-packages %s" % \
          (virtenv_path, cephp_root, pkg_zstacklib, cephp_root, pkg_cephpagent, virtenv_path)
run_remote_command(command, host_post_info)
# name: copy zstacklib
copy_arg = CopyArg()
copy_arg.src="files/zstacklib/%s" % pkg_zstacklib
copy_arg.dest="%s/%s" % (cephp_root,pkg_zstacklib)
zstack_lib_copy = copy(copy_arg, host_post_info)
#if zstack_lib_copy == "changed:true":
pip_install_arg = PipInstallArg()
pip_install_arg.name="%s/%s" % (cephp_root,pkg_zstacklib)
pip_install_arg.extra_args="\"--ignore-installed --trusted-host %s -i %s \"" % (trusted_host,pip_url)
pip_install_arg.virtualenv="%s" % virtenv_path
pip_install_package(pip_install_arg,host_post_info)
# name: copy ceph primarystorage agent
copy_arg = CopyArg()
copy_arg.src="%s/%s" % (file_root,pkg_cephpagent)
copy_arg.dest="%s/%s" % (cephp_root,pkg_cephpagent)
cephpagent_copy = copy(copy_arg, host_post_info)
#if cephpagent_copy  == "changed:true":
pip_install_arg = PipInstallArg()
pip_install_arg.name="%s/%s" % (cephp_root,pkg_cephpagent)
pip_install_arg.extra_args="\"--ignore-installed --trusted-host %s -i %s\"" % (trusted_host,pip_url)
pip_install_arg.virtualenv="%s" % virtenv_path
pip_install_package(pip_install_arg,host_post_info)
# name: copy service file
# only support centos redhat debian and ubuntu
copy_arg = CopyArg()
copy_arg.src="%s/zstack-ceph-primarystorage" % file_root
copy_arg.dest="/etc/init.d/"
copy_arg.args = "mode=755"
copy(copy_arg, host_post_info)
# name: restart cephpagent
service_status("name=zstack-ceph-primarystorage state=restarted enabled=yes", host_post_info)

host_post_info.start_time = start_time
handle_ansible_info("SUCC: Deploy ceph primary agent successful", host_post_info, "INFO")

sys.exit(0)