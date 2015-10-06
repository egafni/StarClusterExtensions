from fabric.api import run
import datetime


def tobool(x):
    if isinstance(x, bool):
        return x
    elif x == 'True':
        return True
    elif x == 'False':
        return False
    else:
        raise ValueError('Bad bool value: %s' % x)

def apt_update(checkfirst=True):
    s = run('stat -c %y /var/lib/apt/periodic/update-success-stamp')[0]
    dt = datetime.now() - datetime.strptime(s[:10],"%Y-%m-%d")
    if not checkfirst or dt.days > 2:
        run('apt-get update -y')