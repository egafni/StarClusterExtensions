def apt_get_install(packages):
    return "DEBIAN_FRONTEND=noninteractive apt-get -y install %s" % packages
