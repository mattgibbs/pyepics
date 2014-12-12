#!/bin/bash

ulimit -c unlimited
while [ /bin/true ]; do
    python sg_simple.py
done;
