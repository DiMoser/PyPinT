#!/bin/sh
make clean && make html && chmod -R go+rX build/html
rm *_debug.log
