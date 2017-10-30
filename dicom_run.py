from glob import glob
import pandas as pd
import numpy as np
import csv
import os
import matplotlib.pyplot as plt
from subprocess import check_output
from subprocess import Popen, PIPE
import shutil
import subprocess 
from subprocess import check_call



for files in os.listdir("/data/pelletier1/genentech/sienax_yr89_lst_lesions/"):
    msid = files.split("-")[0]
    if not msid.startswith("ms"): 
        continue
    if msid.startswith("ms00"):
        msid = "ms" + msid[-2:]
    elif msid.startswith("ms0"):
        msid = "ms" + msid[-3:]
    else:
        msid = msid
    if not os.path.exists("/data/henry7/PBR/subjects/" + msid + "/MNI/"):
        text_file = "/data/henry6/mindcontrol_ucsf_env/watchlists/long/VEO/EPIC_ms/" + msid + ".txt"
        if os.path.exists(text_file):
            with open(text_file) as f: 
                content = f.read().splitlines()
                for mse in content:
                    #print(item)
                    if not os.path.exists("/working/henry_temp/PBR/dicoms/" + mse):
                        print(mse)
                        new_mse = mse.replace("mse", "")
                        try:
                            cmd = ['ms_dcm_qr', '-t', new_mse,'-e',"/working/henry_temp/PBR/dicoms/" + mse]
                            print(cmd)
                            check_call(cmd)
                        except Exception:
                            pass

