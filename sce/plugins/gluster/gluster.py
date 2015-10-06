"""
Sets all the ephemeral drives on the master node to one gluster volume which is mounted
across all worker nodes.

Example config entry:
[plugin glusterfs]
setup_class = gluster.Setup
#stripe of 1 means no stripe
stripe = 1

author: Erik Gafni
"""
import re
import os
from sce import log
from sce.utils.misc import trace


@trace
def mount_brick(node, device, export_path, format=True):
    """
    Formats and mounts a brick
    :param node: (node) The node to format and mount on
    :param device: (str) The path to the device. ie /dev/xvdb1
    :param brick_number: (int) The brick number [0,1,2,3...]
    """
    if is_mounted(node, device):
        unmount(node, device)
        # this is necessary if node wasn't unmounted from a gluster volume cleanly
        # node.ssh.execute('setfattr -x trusted.glusterfs.volume-id {0} ' \
        # '&& setfattr -x trusted.gfid {0} ' \
        # '&& rm -rf {0}/.glusterfs'.format(export_path), silent=True, ignore_exit_status=True, log_output=False)

    if format:
        format_device(node, device)
    mount(node, device, export_path)
    node.ssh.execute('mkdir -p {0}'.format(os.path.join(export_path, 'gluster')))  # gluster mounts a subdir of a mount point


def get_brick_uris(node):
    """
    :returns: (str) "master:brick1.export_path master:brick2.export_path ..."
    """
    return ' '.join('%s:%s/gluster' % (node.alias, line.split()[-1]) for line in
                    node.ssh.execute('df |grep exports/brick', silent=True, ignore_exit_status=True, log_output=False))

    # return " ".join(map(lambda p: 'master:{0}'.format(p), self.device2export_path.values()))


@trace
def format_device(node, device):
    """
    Formats device
    :param node: the node.
    :param device: path to the device.
    """
    # r = node.ssh.execute('file -s {0}'.format(device))
    node.ssh.execute('mkfs.xfs {0} -f'.format(device))
    # if not re.search("XFS filesystem", r[0]):
    #     node.ssh.execute('mkfs.xfs {0} -f'.format(device))
    # else:
    #     log.info('{0} already formatted, skipping'.format(device))


@trace
def unmount(node, device, skipif=None):
    """
    Unmounts a device if it is mounted.
    :param device: (str) path to the device.
    :param skipif: (str) if device is mounted to skipif, do not unmount
    """
    if is_mounted(node, device, skipif):
        log.info('Unmounting {0}'.format(device))
        node.ssh.execute('umount {0}'.format(device))


@trace
def mount(node, device, path, unmount=False):
    """
    Mounts device to path on node
    :param unmount: (bool) if True, attempt unmount first.
    """
    if unmount:
        unmount(node, device, skipif=path)
    node.ssh.execute('mkdir -p {1} && mount {0} {1}'.format(device, path))


def volume_exists(node, volume_name):
    return len(node.ssh.execute('gluster volume info %s' % volume_name, ignore_exit_status=True, silent=True, log_output=False)) > 2


@trace
def create_and_start_volume(node, name, stripe, replicate):
    """
    Creates and starts a volume
    :param node: (node) node to create the volume on
    :param name: (str) name of the volume
    :param stripe: (int) stripe count. <=1 means no stripes.
    :param replicate: (int) replicate count. <=1 means no replicas.
    """
    if volume_exists(node, name):
        log.info('volume %s exists, skipping' % (name))
    else:
        node.ssh.execute('gluster volume create {name}{replicate}{stripe} transport tcp {bricks}'.format(
            name=name,
            bricks=get_brick_uris(node),
            stripe=' stripe {0}'.format(stripe) if int(stripe) > 1 else '',
            replicate=' replica {0}'.format(replicate) if int(replicate) > 1 else '')
        )
        node.ssh.execute('gluster volume start {0}'.format(name))


@trace
def mount_volume(node, volume, mountpoint):
    """
    Mounts gluster to a node
    :param node: the node to mount on
    :param volume: the name of the volume
    :param path: the root directory to mount the volume to.  Volume will be mounted to path/volume
    """

    if not node.ssh.path_exists(mountpoint):
        log.info("Creating volume at mountpoint %s" % mountpoint)
        node.ssh.execute("mkdir -p %s" % mountpoint)

    device = 'master:%s' % volume

    if is_mounted(node, device, mountpoint):
        log.info('%s is already mounted to %s, skipping' % (device, mountpoint))
    else:
        node.ssh.execute('mount -t glusterfs %s %s' % (device, mountpoint))


def is_mounted(node, device, to=None):
    mm = get_mount_map(node)
    if to is not None:
        return mm.get(device, None) == to
    else:
        return device in mm


def get_mount_map(node):
    mount_map = {}
    mount_lines = node.ssh.execute('mount', silent=True)
    for line in mount_lines:
        dev, on_label, path, type_label, fstype, options = line.split()
        mount_map[dev] = [path, fstype, options]
    return mount_map