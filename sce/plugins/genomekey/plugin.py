from starcluster.clustersetup import ClusterSetup
from starcluster.logger import log
from fabric.api import execute as fab_execute, env
import os
from .fab.aws import init_node, init_master
from .fab.gk import copy_genomekey_dev_environ
from .util import tobool
from sce.utils.node import execute, get_mount_map, get_device_map


def run_fab(func, hosts, *args, **kwargs):
    """
    :param hosts: starcluster Nodes
    """
    # TODO get rid of fabric
    if not isinstance(hosts, list):
        hosts = [hosts]

    env.key_filename = [hosts[0].key_location]  # Assume all hosts use the same key...
    env.abort_on_promts = True
    log.info('Run fab task: %s, key_filename=%s, args: %s, kwargs: %s' % (func.__name__, env.key_filename, args, kwargs))
    kwargs['hosts'] = [h.ip_address for h in hosts]
    fab_execute(func, *args, **kwargs)


class GenomeKeySetup(ClusterSetup):
    """
    Interface for StarCluster to use the fab files.  There should be very minimal logic here.
    """

    def __init__(self, install_dev_environ=True, setup_master_scratch=False, **kwargs):
        self.install_dev_environ = tobool(install_dev_environ)
        self.setup_master_scratch = setup_master_scratch
        super(ClusterSetup, self).__init__(**kwargs)


    def run(self, nodes, master, user, user_shell, volumes):
        for node in nodes:
            # fab -f init_node -H $hosts
            run_fab(init_node, hosts=node)

        run_fab(init_master, hosts=master)
        if self.setup_master_scratch:
            run_fab(raid0_scratch_space, hosts=master)


        print 'ASDFSDF', self.install_dev_environ
        if os.path.exists(os.path.expanduser('~/projects/GenomeKey')) and os.path.exists(os.path.expanduser('~/projects/Cosmos')) :
            run_fab(copy_genomekey_dev_environ, hosts=master)



        # Print out_dir IP address for the user
        cluster_name = master.parent_cluster.name[4:]
        etc_hosts_line = "{0}\t{1}".format(master.ip_address, cluster_name)
        log.info('Consider adding to /etc/hosts: %s' % etc_hosts_line)


    def on_add_node(self, node, nodes, master, user, user_shell, volumes):
        raid0_scratch_space(node)


def raid0_scratch_space(node):
    """
    Setup RAID0 with all available ephemeral discs
    """
    print 'Setting up raid 0 for scratch space'

    # node.apt_install("mdadm --no-install-recommends")
    mount_map = get_mount_map(node)
    if '/dev/md0' in mount_map:
        log.info('/dev/md0 already mounted, skipping')
    else:
        ephemeral_devices = [device for device in get_device_map(node) if device.startswith('/dev/xvda')]
        for device in ephemeral_devices:
            if device in mount_map:
                execute(node, 'umount %s' % mount_map[device])

            execute(node, 'mkdir -p /scratch')
            execute(node,
                    'mdadm --create -R --verbose /dev/md0 --level=0 --name=SCRATCH --raid-devices=%s %s' % (len(ephemeral_devices), ' '.join(ephemeral_devices)))
            execute(node, 'sudo mkfs.ext4 -L SCRATCH /dev/md0')
            execute(node, 'mount LABEL=SCRATCH /scratch')
            execute(node, 'chown -R genomekey:genomekey /scratch')



