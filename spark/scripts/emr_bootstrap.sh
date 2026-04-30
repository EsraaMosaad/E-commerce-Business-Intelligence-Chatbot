#!/bin/bash
# spark/scripts/emr_bootstrap.sh
# EMR Bootstrap Action - installs Python dependencies on all nodes

echo "====== EMR Bootstrap: Installing Python dependencies ======"
echo "Node: $(hostname), Started: $(date)"
echo "Python3 binary: $(which python3)"
echo "Python3 version: $(python3 --version)"

# Install packages directly into /usr/bin/python3
sudo /usr/bin/python3 -m pip install --upgrade pip 2>/dev/null || true
sudo /usr/bin/python3 -m pip install --ignore-installed \
    pandas \
    numpy \
    pyarrow \
    fastparquet \
    requests \
    boto3 \
    scikit-learn

which python || sudo ln -sf /usr/bin/python3 /usr/bin/python

echo "====== Bootstrap Complete at $(date) ======"