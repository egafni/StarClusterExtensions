from fabric.api import run
from datetime import datetime


def tobool(x):
    if isinstance(x, bool):
        return x
    elif x == 'True':
        return True
    elif x == 'False':
        return False
    else:
        raise ValueError('Bad bool value: %s' % x)

def apt_update(force=True):
    if not force:
        # TODO this code seems to be broken?
        s = run('stat -c %y /var/lib/apt/periodic/update-success-stamp')
        dt = datetime.now() - datetime.strptime(s[:10],"%Y-%m-%d")
        if dt.days < 2:
            return

    run('apt-get update -y')