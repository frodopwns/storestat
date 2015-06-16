#Storestat

##Running Via Vagrant and Ansible:

###Prereqs

    sudo apt-get install virtualbox
    sudo apt-get install vagrant
    sudo pip install ansible

###Running

    vagrant up
    vagrant ssh
    cd /vagrant
    python test.py
    
When finished the reports can be found in /vagrant/app/reports from within the VM or app/reports where you cloned the storestat repo.

The server and client log files will be in the directory where you ran test.py.  Normally /vagrant.

##Running locally (Ubuntu 12.04)

    sudo apt-get install redis-server python-dev python-pip
    sudo pip install tornado jinja2 redis pygal
    cd app/
    python test.py
    ls -lt reports/

##Viewing the reports

The reports must be opened in a browser from the directory where they are saved (css is lined relatively).

##Configuration

    python client.py --help
    Usage: client.py [options]

    Options:
      -h, --help      show this help message and exit
      --d=DURATION    Number of seconds the test should run (default is 30)
      --f=FILE_SIZE   max size in bytes for files to be written (default 10000000)
      --c=CHUNK_SIZE  size of chunks to be written (default 1000000)
      --dest=DEST     destination to write to (default /tmp)
      --fqdn=FQDN     server address (default http://localhost:8000)
