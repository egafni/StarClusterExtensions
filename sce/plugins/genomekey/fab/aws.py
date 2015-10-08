from fabric.contrib import files
from fabric.api import cd, task, run, sudo, settings, hide, shell_env
import glob
from sce.plugins.genomekey.util import apt_update

GENOME_KEY_USER = 'genomekey'

def apt_get_install(packages):
    return run('apt-get -q -y install %s' % packages)

# class CheckPoint():
#     def __init__(self, path):
#         self.path = path
#     def __enter__(self):
#         return files.exist(self.path)
#     def __exit__(self, exc_type, exc_val, exc_tb):
#         run('touch %s' % self.path)

@task
def init_node():
    with hide('output'), settings(user='root'):
        CP = '/etc/apt/sources.list.updated'
        if not files.exists(CP):
            # TODO get rid of this pastebin.  The StarCluster AMI has whack apt sources.
            run('wget "http://pastebin.com/raw.php?i=uzhrtg5M" -O /etc/apt/sources.list')
            apt_update(force=True)
            run('touch %s' % CP)

        if not ('Java(TM) SE Runtime Environment' in run('java -version')):
            run('add-apt-repository ppa:webupd8team/java -y')
            apt_update(force=True)

            # debconf so java install doesn't prompt for license confirmation
            run('echo oracle-java7-installer shared/accepted-oracle-license-v1-1 select true | /usr/bin/debconf-set-selections')
            apt_get_install('oracle-java7-installer oracle-java7-set-default')

        apt_get_install('libcurl4-openssl-dev')


        # setup /scratch.  Currently just using the gluster volume.
        run('ln -f -s /gluster/gv0/analysis /genomekey/analysis')
        run('chown -R genomekey:genomekey /genomekey')  # TODO fix the perms in the ami

        # setup_scratch_space() - Using gluster.

        with settings(user=GENOME_KEY_USER):
            setup_aws_cli(True)
            sync_genomekey_share()


@task
def init_master():
    # Note comes after init_node()

    with hide('output'), settings(user='root'):
        run('chown -R genomekey:genomekey /gluster/gv0')
        run('mkdir -p /gluster/gv0/analysis')

        # update apt-list, starcluster AMI is out_dir-of-date
        apt_get_install('graphviz graphviz-dev mbuffer')
        run('pip install awscli')

        # For ipython notebook.  Do this last user can get started.  Installing pandas is slow.
        run('pip install "ipython[notebook]>3"')


        with settings(user=GENOME_KEY_USER):


            files.append('~/.bashrc', ['export SGE_ROOT=/opt/sge6',
                                       'export PATH=$PATH:/opt/sge6/bin/linux-x64:$HOME/bin'])


def sync_genomekey_share():
    """
    Requires that setup_aws_cli() has already been called
    """
    # with settings(user='root'):
    # TODO change the AMI and delete this?  This runs instantly so not a big deal
    # run('chown -R genomekey:genomekey /genomekey')
    print 'sync genomekey share'
    with hide('output'):
        run('aws s3 sync s3://genomekey-data /genomekey/share')
        chmod_opt('/genomekey/share/opt')


def chmod_opt(opt_path):
    with cd(opt_path):
        # TODO use settings to decide what to chmod?
        bins = ['bwa/*/bwa',
                'samtools/*/samtools',
                'gof3r/*/gof3r',
                'fastqc/*/fastqc',
                'cutadapt/*/bin/cutadapt',
                'bin/run']

        for b in bins:
            # aws s3 cli doesn't preserve file perms :(
            run('chmod +x %s' % b)


def setup_aws_cli(overwrite=False):
    if overwrite or not files.exists('~/.aws/config'):
        run('mkdir -p ~/.aws')

        # push aws config files
        files.upload_template('config', '~/.aws/config', use_jinja=False, template_dir='~/.aws')
        files.upload_template('credentials', '~/.aws/credentials', use_jinja=False, template_dir='~/.aws')


# @taska
# def mount_genomekey_share(mount_path='/mnt/genomekey/share_yas3fs'):
# with aws_credentials(), settings(user='root'):
# run('pip install yas3fs')
# if mount_path not in run('cat /proc/mounts', quiet=True):
# run('mkdir -p %s' % mount_path)
#             run('yas3fs --region us-west-2 --cache-path /mnt/genomekey/tmp/genomekey-data '
#                 's3://genomekey-data %s' % mount_path)
#
#             chmod_opt(os.path.join(mount_path, 'opt'))
#             # '--topic arn:aws:sns:us-west-2:502193849168:genomekey-data --new-queue --mkdir')

