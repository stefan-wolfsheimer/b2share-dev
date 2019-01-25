#!/bin/bash -x
supervisorctl start celery
supervisorctl start celery_beat

sleep 30

/build/b2share.py demo load_config
/build/b2share.py db init
/build/b2share.py upgrade run -v
sleep 20
/build/b2share.py demo load_data


touch /usr/var/b2share-instance/provisioned

/build/b2share.py run -h 0.0.0 
