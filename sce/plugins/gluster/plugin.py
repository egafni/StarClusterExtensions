__author__ = 'Erik Gafni'

"""
Sets all the ephemeral drives on the master node to one gluster volume which is mounted
across all worker nodes.

Example config entry:

[plugin glusterfs]
setup_class = gluster.Setup
stripe = 2

author: Erik Gafni
"""
import os

from starcluster import threadpool

from sce import log
from . import gluster
from starcluster.clustersetup import ClusterSetup
from sce.utils.shell import apt_update
from ...utils.node import execute


VOLUME_NAME = 'gv0'


class GlusterSetup(ClusterSetup):
    _pool = None

    def __init__(self, stripe=0, replicate=0, **kwargs):
        self.stripe = stripe
        self.replicate = replicate
        super(GlusterSetup, self).__init__(**kwargs)

    @property
    def pool(self):
        if self._pool is None:
            self._pool = threadpool.get_thread_pool(4, disable_threads=False)
        return self._pool


    def run(self, nodes, master, user, user_shell, volumes):
        install_gluster(master)
        if gluster.volume_exists(master, VOLUME_NAME):
            log.info('volume %s exists, removing' % (VOLUME_NAME))

            master.ssh.execute('gluster volume delete %s --mode=script' % VOLUME_NAME)
        else:
            setup_bricks(master)

            gluster.create_and_start_volume(master, VOLUME_NAME, self.stripe, self.replicate)
            gluster.mount_volume(master, VOLUME_NAME, '/gluster/%s' % VOLUME_NAME)

        execute(master, 'mkdir -p /gluster/gv0/master_scratch')
        execute(master, 'ln -f -s /gluster/gv0/master_scratch /scratch')


    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        install_gluster(node)
        gluster.mount_volume(node, VOLUME_NAME, '/gluster/%s' % VOLUME_NAME)


def install_gluster(node):
    log.info('Installing gluster packages.')
    if 'glusterfs 3.5' in node.ssh.execute('gluster --version', silent=True, ignore_exit_status=True, log_output=False)[0]:
        log.info('Gluster already installed, skipping')
    else:
        node.ssh.execute('sudo add-apt-repository ppa:gluster/glusterfs-3.5 -y')
        apt_update(node, checkfirst=False)
        node.apt_install('glusterfs-server glusterfs-client software-properties-common xfsprogs attr openssh-server')


def setup_bricks(node):
    log.info('Partitioning and formatting ephemeral drives.')
    # TODO i'm not sure if theres a better way to get ephemeral_devices
    ephemeral_devices = execute(node, 'ls /dev/xvda*',
                                ignore_exit_status=True)
    log.info("Gathering devices for bricks: %s" % ', '.join(ephemeral_devices))

    for brick_number, device in enumerate(ephemeral_devices):
        export_path = os.path.join('/exports', 'brick%s' % brick_number)
        gluster.mount_brick(node, device, export_path)

        # self.pool.simple_job(gluster.mount_brick, (master, device, export_path), jobid=device)
        # self.pool.wait(len(ephemeral_devices))
