import re

def cluster_name(node):
    return node.parent_cluster.name.replace('@sc-', '')


def node_str_to_node(cluster, node_str):
    if node_str == 'ALL':
        return cluster.nodes
    else:
        return filter(lambda n: n.alias == node_str, cluster.nodes)[0]



def execute(node, cmd, silent=True, log_output=True, **kwargs):
    return node.ssh.execute(cmd, silent=silent, log_output=log_output, **kwargs)



def get_mount_map(node, details=False):
    mount_map = {}
    mount_lines = execute(node, 'mount')
    for line in mount_lines:
        dev, on_label, path, type_label, fstype, options = line.split()
        if details:
            mount_map[dev] = [path, fstype, options]
        else:
            mount_map[dev] = path
    return mount_map

def get_device_map(node):
    """
    Returns a dictionary mapping devices->(# of blocks) based on
    'fdisk -l' and /proc/partitions
    """
    dev_regex = '/dev/[A-Za-z0-9/]+'
    r = re.compile('Disk (%s):' % dev_regex)
    fdiskout = '\n'.join(execute(node, "fdisk -l 2>/dev/null"))
    proc_parts = '\n'.join(execute(node, "cat /proc/partitions"))
    devmap = {}
    for dev in r.findall(fdiskout):
        short_name = dev.replace('/dev/', '')
        r = re.compile("(\d+)\s+%s(?:\s+|$)" % short_name)
        devmap[dev] = int(r.findall(proc_parts)[0])
    return devmap