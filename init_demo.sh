#!/bin/bash -x
supervisorctl start celery
supervisorctl start celery_beat

sleep 30

/build/b2share.py demo load_config
/build/b2share.py db init
/build/b2share.py upgrade run -v
sleep 20
# create fake DOIs
export B2SHARE_DEMO_CFG_FAIL_ON_MISSING_PID=1 
export B2SHARE_DEMO_CFG_FAIL_ON_MISSING_DOI=1
export B2SHARE_DEMO_FAKE_EPIC_PID=1
export B2SHARE_DEMO_FAKE_DOI=1

/build/b2share.py demo load_data


touch /usr/var/b2share-instance/provisioned

/build/b2share.py run -h 0.0.0 
