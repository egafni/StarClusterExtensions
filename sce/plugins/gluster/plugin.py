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
        if not gluster.volume_exists(master, 'gv0'):
            setup_bricks(master)
            gluster.create_and_start_volume(master, 'gv0', self.stripe, self.replicate)

            gluster.mount_volume(master, 'gv0', '/gluster/gv0')



    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        install_gluster(node)
        setup_bricks(node)

        master.ssh.execute('gluster peer probe %s' % node.alias)
        # node.ssh.execute('')


def install_gluster(node):
    log.info('Installing gluster packages.')
    if 'glusterfs 3.5' in node.ssh.execute('gluster --version', silent=True, ignore_exit_status=True, log_output=False):
        log.info('Gluster already installed, skipping')
    else:
        node.ssh.execute('sudo add-apt-repository ppa:gluster/glusterfs-3.5 -y')
        apt_update(node, checkfirst=False)
        node.apt_install('glusterfs-server glusterfs-client software-properties-common xfsprogs attr openssh-server')


def setup_bricks(node):
    log.info('Partitioning and formatting ephemeral drives.')
    ephemeral_devices = node.ssh.execute('ls /dev/xvd*', silent=True,
                                         ignore_exit_status=True)  # TODO i'm not sure this logic to find ephemeral_devices applies to non c3.4xlarge...
    log.info("Gathering devices for bricks: %s" % ', '.join(ephemeral_devices))

    for brick_number, device in enumerate(ephemeral_devices):
        export_path = os.path.join('/exports', 'brick%s' % brick_number)
        gluster.mount_brick(node, device, export_path)

        # self.pool.simple_job(gluster.mount_brick, (master, device, export_path), jobid=device)
    # self.pool.wait(len(ephemeral_devices))
