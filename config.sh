#!/bin/bash

# Configure these parameters according to your needs.
# See https://cloud.google.com/compute/docs/gpus/add-gpus#create-new-gpu-instance for more details.

# the name of the created instance
INSTANCE_NAME=lizzieeuc

# can be either "best" or "elf" for the facebook opengo converted weights (currently stronger, slower)
NETWORK=best

# pick a nearby zone that has the gpu you want - see https://cloud.google.com/compute/docs/gpus/
#ZONE=us-central1-f
ZONE=europe-west4-c
# Zones for v100
#    us-west1-a # 4gpus
#    us-west1-b
#    us-central1-a
#    us-central1-b
#    us-central1-f
#    europe-west4-a # 10 gpus
#    europe-west4-b
#    europe-west4-c
#    asia-east1-c # 10 gpus

# can be k80, p100, v100 - see README.md
GPU_TYPE=nvidia-tesla-v100

# the number of gpus (one should usually be enough)
GPU_COUNT=1

# the number of cpus you seem fit for your gpu - should be an even number
CPU_COUNT=6

# 10GB should be plenty of space for just leela zero.. You might get away with less
DISK_SIZE=10GB

# Set the RAM here - not sure how much is needed for leela
MEMORY=15GB

# Only touch these if you know what you're doing. You will need to adapt the setup script for other Linux distributions.
IMAGE_FAMILY=ubuntu-1604-lts
IMAGE_PROJECT=ubuntu-os-cloud
