#!/bin/bash
sudo apt-get update
sudo apt-get install -y postgresql
sudo systemctl start postgresql
sudo -u postgres psql -c "CREATE USER test WITH PASSWORD 'test' SUPERUSER;"
sudo -u postgres psql -c "CREATE DATABASE test_integration;"
