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


"""for mse in os.listdir("/working/henry_temp/PBR/dicoms/"): 
    #for E in os.listdir("/working/henry_temp/PBR/dicoms/" + mse):
    if os.path.isdir("/working/henry_temp/PBR/dicoms/" + mse) and mse.startswith("mse"):
        if os.listdir("/working/henry_temp/PBR/dicoms/" + mse) == []:
            print(mse, "empty")
            #os.removedirs("/working/henry_temp/PBR/dicoms/" + mse)
            mse_num = mse.replace("mse", "")
            cmd = ["ms_dcm_qr", "-t", mse_num]
            proc = Popen(cmd, stdout=PIPE)
            output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]
            print(cmd, mse, "empty")
            break
        
        else:
            print(mse)"""

"""for mse in os.listdir("/working/henry_temp/PBR/dicoms/"): 
    #for E in os.listdir("/working/henry_temp/PBR/dicoms/" + mse):
    if os.path.isdir("/working/henry_temp/PBR/dicoms/" + mse) and mse.startswith("mse"):
        if os.listdir("/working/henry_temp/PBR/dicoms/" + mse) == []:
            print(mse, "empty")
            
            #os.removedirs("/working/henry_temp/PBR/dicoms/" + mse)
            mse_num = mse.replace("mse", "")
            cmd = ["ms_dcm_qr", "-t", mse_num]
            print(cmd)
            proc = Popen(cmd, stdout=PIPE)
            output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]
            print(cmd, mse, "empty")
            #shutil.move("/working/henry_temp/PBR/dicoms/glob(ms*)" + mse,"/working/henry_temp/PBR/dicoms/"+ mse)
            msid_filename = glob("/working/henry_temp/PBR/dicoms/ms*" + mse)
            print(msid_filename)
            #print("/working/henry_temp/PBR/dicoms/glob(ms*)" + mse,"/working/henry_temp/PBR/dicoms/"+ mse)
            break
        
        else:
            continue"""

for mse in os.listdir("/data/henry7/PBR/subjects"):
    if mse.startswith("mse"):
        for files in os.listdir("/data/henry7/PBR/subjects/" + mse):
            if "alignment" in files:
                if not "mni_angulated" in os.listdir("/data/henry7/PBR/subjects/" + mse + "/alignment/"):
                    print(mse)
                    shutil.rmtree("/data/henry7/PBR/subjects/" + mse + "/alignment/")
                    print("/data/henry7/PBR/subjects/" + mse + "/alignment/")
                    if os.path.exists("/working/henry_temp/keshavan/MNIAng_" + mse):
                        print("/working/henry_temp/keshavan/MNIAng_" + mse)
                        shutil.rmtree("/working/henry_temp/keshavan/MNIAng_" + mse)
                    #status = "/data/henry7/PBR/subjects/" + mse + "/nii/status.json"
                    #if status.is_file():
                        #shutil.rmtree("/data/henry7/PBR/subjects/" + mse + "/nii/status.json")
                    try: 
                        cmd = ["pbr", mse, "-w", "nifti", "align", "-R", "-ps", "Rosie1313"]
                        check_call(cmd)
                        Popen(cmd, stdout=PIPE)
                        Popen.wait()
                        print(cmd)
                    except Exception:
                        pass
