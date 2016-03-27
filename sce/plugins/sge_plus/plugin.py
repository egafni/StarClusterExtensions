"""
Configures SGE to work with h_vmem and other complex values.

This means you can submit jobs, specify how much memory you require, and Grid Engine will
be able to schedule properly.

To schedule jobs, use -l like this: qsub -l sce_mem=10G,num_proc=3

Example config:
[plugin sge_plus]
SETUP_CLASS = sce.plugins.sge_plus.plugin.SGE_Plus_Setup

Useful commands:
qconf -sc
qconf

"""
import os
import subprocess as sp

from starcluster.logger import log
from starcluster.clustersetup import ClusterSetup
from sce.utils.misc import trace
from sce.utils.node import execute

opj = os.path.join


class SGE_Plus_Setup(ClusterSetup):
    def __init__(self, master_slots=1, **kwargs):
        self.data_path = opj(os.path.dirname(__file__), 'data')
        self.master_slots = master_slots
        super(SGE_Plus_Setup, self).__init__(**kwargs)

    @trace
    def run(self, nodes, master, user, user_shell, volumes):
        log.info('Running SGE Plus')

        # update qconf complex list to make h_vmem and num_proc consumable
        log.info('Update complex configuration')
        master.ssh.put(opj(self.data_path, 'qconf_c'), '/tmp/qconf_c')
        execute(master, 'qconf -Mc /tmp/qconf_c')
        log.info('Update ms configuration')
        master.ssh.put(opj(self.data_path, 'msconf'), '/tmp/msconf')
        execute(master, 'qconf -Msconf /tmp/msconf')

        for node in nodes:
            self.on_add_node(node, nodes, master, user, user_shell, volumes)


    @trace
    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        update_complex_list(node, num_proc=self.master_slots if node.is_master() else None)


@trace
def update_complex_list(node, num_proc=None):
    """
    Sets a node's h_vmem and num_proc complex values

    :param node: The node to update
    """
    log.info('Updating complex values for {0}'.format(node))
    memtot = execute(node, 'free -g|grep Mem:|grep -oE "[0-9]+"|head -1')[0]

    num_proc = num_proc if num_proc else execute(node, 'nproc')[0]
    # scratch_mb= sp.check_output('df |grep scratch',shell=True).split()[3]
    scratch_mb = 0

    if node.is_master():
        num_proc = int(num_proc / 2)

    execute(node,
            "qconf -rattr exechost complex_values slots={num_proc},num_proc={num_proc},sce_mem={mem}g,sce_scratch={scratch_mb} {node}".format(
                mem=memtot, num_proc=num_proc, node=node.alias, scratch_mb=scratch_mb)
    )

    log.info('Done updating complex values')