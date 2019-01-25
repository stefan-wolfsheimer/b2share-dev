#!/bin/bash -x

# install webui
echo "install webui"
mkdir -p /build/b2share/webui/app/vendors
cp /eudat/public-license-selector/dist/license-selector.* /build/b2share/webui/app/vendors
cd /build/b2share/webui/
npm install --unsafe-perm
node_modules/webpack/bin/webpack.js -p

echo "start with:"
echo "uwsgi --ini /build/uwsgi.ini"

