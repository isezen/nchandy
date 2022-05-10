#!/bin/bash

rm -rf build
rm -rf dist
rm -rf nchandy.egg-info
find . -name '*.pyc' -print0 | xargs -0 rm