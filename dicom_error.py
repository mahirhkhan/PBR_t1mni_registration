from getpass import getpass
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


for mse in os.listdir("/working/henry_temp/PBR/dicoms/"): 
    #for E in os.listdir("/working/henry_temp/PBR/dicoms/" + mse):
    if os.path.isdir("/working/henry_temp/PBR/dicoms/" + mse) and mse.startswith("mse"):
        if os.listdir("/working/henry_temp/PBR/dicoms/" + mse) == []:
            print(mse, "empty")
            password = "Rosie1313"
            mse_path = "/working/henry_temp/PBR/dicoms/" + mse
            try: 
                cmd = ['ms_dcm_qr', '-t', mse[3:],'-e',"/working/henry_temp/PBR/dicoms/", '-p', password]
                        #cmd = ["pbr", mse, "-w", "nifti", "align", "-R", "-ps", "Rosie1313"]
                check_call(cmd)
                Popen(cmd, stdout=PIPE)
                Popen.wait()
                print(cmd)
            except Exception:
                pass
