import os
from glob import glob
from subprocess import Popen, PIPE
import json
from nipype.interfaces import fsl
from nipype.interfaces.fsl import RobustFOV, Reorient2Std
from nipype.interfaces.c3 import C3dAffineTool
import argparse
import shutil 
from nipype.interfaces.fsl import BinaryMaths, UnaryMaths, ErodeImage, ImageStats, Threshold, DilateImage
import numpy as np 
import math 
from nipype.interfaces.base import CommandLine, CommandLineInputSpec, SEMLikeCommandLine, TraitedSpec, File, Directory, traits, isdefined, InputMultiPath, OutputMultiPath



"takes the difference between the two flair scans at different timepoints, multiplies the difference by the wm mask (created from sienax), create zscore image, multiplies that images by the lst lesion mask, and thresholds that image to get a new lesion mask" 


PBR_base_dir = '/data/henry7/PBR/subjects/'

class imageData():
    def __init__(self, lesion_MNI, wm_MNI, flair_file, t1_file, gm_MNI):
        self.lesion_MNI = lesion_MNI
        self.wm_MNI = wm_MNI
        self.gm_MNI = gm_MNI
        self.flair_file = flair_file
        self.t1_file = t1_file


def find_lesion_MNI(mseid): 

    if not os.path.exists(PBR_base_dir+"/"+mseid+"/alignment/status.json"):
        run_pbr_align(mseid)
    
    with open(PBR_base_dir+"/"+mseid+"/alignment/status.json") as data_file:  
        data = json.load(data_file)
        if len(data["t1_files"]) == 0:
            print("no {0} t1 files".format(tp))
            run_pbr_align(mseid)
            t1_file = "none"
        else:
            t1_file = data["t1_files"][-1]

        if len(data["flair_files"]) == 0:
            flair_file = "none"
        else:
            flair_file = data["flair_files"][-1]
            flair_file = format_to_baseline_mni(flair_file, "_T1mni.nii.gz")
            print(flair_file)
    

    lesion_MNI = PBR_base_dir+ mseid + "/alignment/baseline_mni/lesion_MNI.nii.gz"
    mni_long = PBR_base_dir + msid + "/MNI/"
    wm_MNI = PBR_base_dir+ mseid + "/alignment/baseline_mni/WM_MNI.nii.gz"
    gm_MNI = PBR_base_dir+ mseid + "/alignment/baseline_mni/GM_MNI.nii.gz"
    
    if os.path.exists(wm_MNI):
        print(wm_MNI)
        if not os.path.exists(mni_long):
            os.mkdir(mni_long)
        
        print(wm_MNI,mni_long + "/wm_"+mseid + ".nii.gz")

    if os.path.exists(gm_MNI):
        print(gm_MNI)
        cmd = ["fslmaths", gm_MNI, "-bin", gm_MNI]
        proc = Popen(cmd, stdout=PIPE)
        output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]

        shutil.copyfile(gm_MNI,mni_long + "/gm_"+mseid + ".nii.gz")
        print(gm_MNI,mni_long + "/gm_"+mseid + ".nii.gz")


    if os.path.exists(lesion_MNI):
        print(lesion_MNI)
    
        if not os.path.exists(mni_long):
             os.mkdir(mni_long)
             print(mni_long)
        if not os.path.exists(mni_long+ "/lesion_"+mseid + ".nii.gz"):
            shutil.copyfile(lesion_MNI,mni_long + "/lesion_"+mseid + ".nii.gz")
            print(lesion_MNI,mni_long + "/lesion_"+mseid + ".nii.gz")
        if flair_file.endswith(".nii.gz"):
            
            flair_path = os.path.split(lesion_MNI)[0] +'/'+ os.path.split(flair_file)[-1]

            shutil.copyfile(flair_path, mni_long +'/'+ os.path.split(flair_path)[-1])
            print(flair_path, mni_long +'/'+ os.path.split(flair_path)[-1])

    return imageData(lesion_MNI, wm_MNI, flair_file, t1_file, gm_MNI)
    print("FINISHED COPYING OVER MNI FILES....")



def run_pbr_align(mseid):

    alignment_folder = "/data/henry7/PBR/subjects/{0}/alignment".format(mseid)
    if os.path.exists(alignment_folder):
        cmd_rm = ['rm','-r', alignment_folder]
        print (cmd_rm)
        proc = Popen(cmd_rm)
        proc.wait()
    
    cmd = ['pbr', mseid, '-w', 'align', '-R']
    print (cmd)
    proc = Popen(cmd)
    proc.wait()

def format_to_baseline_mni(in_file,extension,message="show"):
    out_path = in_file.split("alignment")[0] + "alignment/baseline_mni"
    file_name = in_file.split('/')[-1].split('.')[0] + extension
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    out_file = os.path.join(out_path, file_name)
    return out_file

def format_to_lesion_mni(in_file,extension,message="show"):
    out_path = in_file.split("alignment")[0] + "lesion_mni"
    file_name = in_file.split('/')[-1].split('.')[0] + extension
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    out_file = os.path.join(out_path, file_name)
    return out_file



def create_flair_lesions(mseid, msid):
    find_lesion_MNI(mseid)
    print(mseid, msid)
    mni_long = PBR_base_dir + msid + "/MNI/"
    if not os.path.exists(mni_long):
        print("This subject does not have any FLAIR images to register the lesions to")
    else: 
        with open(PBR_base_dir+"/"+mseid+"/alignment/status.json") as data_file:  
            data = json.load(data_file)
            if len(data["t1_files"]) == 0:
                print("no {0} t1 files".format(tp))
                run_pbr_align(mseid)
                t1_file = "none"
            else:
                t1_file = data["t1_files"][-1]

            if len(data["flair_files"]) == 0:
                flair_file = "none"
            else:
                flair_file = data["flair_files"][-1]
                flair_file = format_to_baseline_mni(flair_file, "_T1mni.nii.gz")
                print(flair_file)

        if os.path.exists(flair_file):
            if not os.path.exists(PBR_base_dir +"/"+mseid + "/lesion_mni"):
                os.mkdir(PBR_base_dir +"/"+mseid + "/lesion_mni")
            

            flair_MNI = str(glob(mni_long + "ms*.nii.gz")[0])
            wm_MNI = str(glob(mni_long + "wm*.nii.gz")[0])
            gm_MNI = str(glob(mni_long + "gm*.nii.gz")[0])
            lesion_MNI = str(glob(mni_long + "lesion_mse*.nii.gz")[0])

            cmd = ["fslmaths", lesion_MNI, "-bin", lesion_MNI.replace("lesion_", "lesion_bin_")]
            proc = Popen(cmd, stdout=PIPE)
            output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]
            
            lesion_bin_MNI = str(glob(mni_long + "lesion_bin_mse*.nii.gz")[0]) 
            

            base_dir =  os.path.split(format_to_lesion_mni(flair_file, "_WM.nii.gz"))[0]
            wm_eroded = base_dir + "/wm_eroded"
            wm_flair = base_dir + "/wm_flair"

            cmd = ["N4BiasFieldCorrection", "-d", "3", "-i", flair_file,"-w", wm_MNI, "-o", flair_file.replace(".nii.gz", "_n4corr.nii.gz")]
            proc = Popen(cmd, stdout=PIPE)
            output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]

            flair_file = flair_file.replace(".nii.gz", "_n4corr.nii.gz")
      
            # calculating estimated median and standard deviation for nawm 

            no_wm = "/data/henry6/PBR/surfaces/MNI152_T1_1mm/mri/no_wm_MNI_new.nii.gz"
            cmd = ["fslmaths", wm_MNI, "-ero","-sub", no_wm, "-thr", ".1", "-mul",flair_file, wm_eroded]
            proc = Popen(cmd, stdout=PIPE)
            output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]

            wm_with_les = base_dir+ "/wm_withles.nii.gz"
            lesion_dil = base_dir + "/lesion_dil.nii.gz"

            cmd = ["bet",flair_file, base_dir + "/skull.nii.gz", "-s"]
            proc = Popen(cmd, stdout=PIPE)
            output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]
            proc.wait()

            cmd = ["fslstats", wm_eroded, "-P", "50"]
            proc = Popen(cmd, stdout=PIPE)
            output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]
            output = output[0]
            median_nawm = float(output[0])
            print(median_nawm, "THIS IS THE MEDIAN of the NAWM")

            cmd = ["fslmaths", base_dir + "/skull.nii.gz", "-uthr",str(median_nawm),"-bin",base_dir+ "/thr.nii.gz"]
            proc = Popen(cmd, stdout=PIPE)
            output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]


            #dilating the lesion mask and subtracting the gray matter 
            cmd = ["fslmaths",lesion_bin_MNI , "-dilM",  "-sub", gm_MNI,"-add", lesion_bin_MNI,"-sub",base_dir+ "/thr.nii.gz", "-thr", ".1","-bin", lesion_dil]  #"-sub", no_wm,
            proc = Popen(cmd, stdout=PIPE)
            output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]

            cmd = ["fslmaths", lesion_dil, "-add", wm_MNI, "-bin", wm_with_les]
            proc = Popen(cmd, stdout=PIPE)
            output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]


            cmd = ["fslmaths", wm_with_les, "-mul",flair_file, wm_flair]
            proc = Popen(cmd, stdout=PIPE)
            output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]


 
            new_median_nawm = median_nawm - .000001
            print("NEW MEDIAN", new_median_nawm)
                

            cmd = ["fslmaths",  wm_eroded, "-uthr", str(new_median_nawm), base_dir+"/ero_WM_Lhalf.nii.gz"]
            proc = Popen(cmd, stdout=PIPE)
            output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]
            print(cmd)

            cmd = ["fslstats", base_dir+ "/ero_WM_Lhalf.nii.gz", "-S"]
            proc = Popen(cmd, stdout=PIPE)
            output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]
            output = output[0]
            std_nawm = float(output[0])
            print(std_nawm, "THIS IS THE STANDARD DEVIATION of NAWM")

            est_std = float(std_nawm) * 1.608 

            cmd = ["fslstats", wm_eroded, "-V"]
            proc = Popen(cmd, stdout=PIPE)
            output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]
            output = output[0]
            vol_nawm = float(output[0])
            print(vol_nawm, "THIS IS THE VOLUME OF THE NAWM")

            #calculate wm histogram 
            std_times2 = std_nawm*std_nawm*2
            print(std_times2, "this is the standard deviation squared times 2")
            part1 = vol_nawm/(math.sqrt(std_times2*(math.pi)))
            print(part1, "this is part1 times 2")
            cmd = ["fslmaths", wm_flair, "-sub",str(median_nawm),"-sqr", "-div", str(std_times2), "-mul", "-1", "-exp", "-mul", str(part1), base_dir+"/wm_hist.nii.gz"] 
            print(cmd, "COMMAND")
            proc = Popen(cmd, stdout=PIPE)
            output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]
            print(cmd)
            
            # calculating estimated median and standard deviation for lesions
            lesion_mul_flair = base_dir + "/lesion.nii.gz"

            """cmd = ["fslmaths", base_dir + "/skull.nii.gz", "-uthrP","60","-bin",base_dir+ "/thr2.nii.gz"]
            proc = Popen(cmd, stdout=PIPE)
            output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]"""

            cmd = ["fslmaths", lesion_bin_MNI,"-sub", base_dir + "/thr.nii.gz", "-thr", ".1", "-bin", "-mul",flair_file,  lesion_mul_flair]
            proc = Popen(cmd, stdout=PIPE)
            output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]

            cmd = ["fslstats", lesion_mul_flair, "-P", "50"]
            proc = Popen(cmd, stdout=PIPE)
            output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]
            output = output[0]
            median_lesion = float(output[0])
            print(median_lesion, "THIS IS THE LESION MEDIAN")
 
            new_median_lesion = median_lesion + .000001
            print("NEW MEDIAN", new_median_lesion)

            cmd = ["fslmaths",  lesion_mul_flair, "-thr", str(new_median_lesion), base_dir+ "/lesion_Uhalf.nii.gz"]
            proc = Popen(cmd, stdout=PIPE)
            output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]
            print(cmd)

            cmd = ["fslstats",base_dir +"/lesion_Uhalf.nii.gz" , "-S"]
            proc = Popen(cmd, stdout=PIPE)
            output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]
            std_lesion = output[0]
            std_lesion = float(std_lesion[0])
            print(std_lesion, "THIS IS THE STANDARD DEVIATION for the lesion upper half")

            est_std = std_lesion * 1.608 
            #echo 20.077990*1.608 | bc

            cmd = ["fslstats", lesion_mul_flair, "-V"]
            proc = Popen(cmd, stdout=PIPE)
            output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]
            output = output[0]
            vol_lesion = float(output[0])
            print(vol_lesion, "THIS IS THE VOLUME OF THE lesion")

            if not vol_lesion == 0.0:
            # lesion histogram 
                lesion_times2 = std_lesion*std_lesion*2
                print(lesion_times2, "thisis the standard deviation times 2")
                part2 = vol_lesion/(math.sqrt(lesion_times2*(math.pi)))
                print(part2, "this is part2 times 2")
                cmd = ["fslmaths", wm_flair, "-sub",str(median_lesion),"-sqr", "-div", str(lesion_times2), "-mul", "-1", "-exp", "-mul", str(part1),base_dir+"/lesion_hist.nii.gz"]
                print(cmd, "COMMAND")
                proc = Popen(cmd, stdout=PIPE)
                output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]
                print(cmd)

                prob_map = base_dir +"/prob_map_new.nii.gz"
                prob_map_nobs = base_dir +"/prob_map_nowmbs.nii.gz"
            

                final_lesion = base_dir + "/lesion_final_new.nii.gz"
                wm_no_bs = base_dir+ "/wm_no_bs.nii.gz"

                # eroding the wm mask and adding in yhr dilated lesion mask
                cmd = ["fslmaths",wm_MNI, "-sub", no_wm, "-thr", ".1","-ero","-add",lesion_dil,"-bin", wm_no_bs] # can try adding back later "-sub",gm_MNI,
                proc = Popen(cmd, stdout=PIPE)
                output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]

                # making the probability map
                cmd = ["fslmaths", base_dir+"/lesion_hist.nii.gz", "-add", base_dir+ "/wm_hist.nii.gz",base_dir+"/add_his.nii.gz"]
                proc = Popen(cmd, stdout=PIPE)
                output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]



                cmd = ["fslmaths",base_dir +"/lesion_hist.nii.gz", "-div",base_dir+ "/add_his.nii.gz","-mul", wm_with_les, prob_map]
                proc = Popen(cmd, stdout=PIPE)
                output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]

                #or just look in the dialated lesion minus the gray matter mask
                cmd = ["fslmaths",lesion_dil,"-mul",prob_map, "-thr", ".95","-bin","-mul",wm_with_les,"-bin", "-sub",base_dir+ "/thr.nii.gz","-thr", ".1", "-bin", final_lesion]
                proc = Popen(cmd, stdout=PIPE)
                output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]



                """cmd = ["fslmaths",final_lesion,"-mul",lesion_MNI, base_dir+ "/lesion_labeled.nii.gz"]
                proc = Popen(cmd, stdout=PIPE)
                output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]"""


                cmd = ["fslmaths",wm_no_bs, "-mul", prob_map, "-ero", prob_map_nobs]
                proc = Popen(cmd, stdout=PIPE)
                output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]

                cmd = ["fslmaths", prob_map_nobs,"-thr", ".999","-sub",base_dir+ "/thr.nii.gz","-thr", ".1", "-bin","-ero","-add",final_lesion, "-bin", base_dir+ "/lesion_prob_map.nii.gz"]
                proc = Popen(cmd, stdout=PIPE)
                output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]

                cmd = ["fslmaths",base_dir+ "/lesion_prob_map.nii.gz", "-dilM", "-mul", prob_map, "-thr", ".9","-sub", base_dir + "/thr2.nii.gz", "-bin", base_dir+ "lesion_prob_map.nii.gz"]
                proc = Popen(cmd, stdout=PIPE)
                output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]

                cmd = ["fslmaths", lesion_MNI, "-dilM", "-mul", base_dir+ "/lesion_prob_map.nii.gz", base_dir+ "/lesion_labeled.nii.gz" ]
                proc = Popen(cmd, stdout=PIPE)
                output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]

   
                cmd = ["fslview",wm_eroded, wm_with_les,prob_map, base_dir+ "/lesion_labeled.nii.gz",final_lesion, lesion_bin_MNI, flair_file,base_dir+ "/lesion_prob_map.nii.gz" ]
                proc = Popen(cmd, stdout=PIPE)
                output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]



           
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('ms', nargs="+")
    args = parser.parse_args()
    ms = args.ms
    print("msid is:", ms)

    
    for msid in ms:
        text_file = '/data/henry6/mindcontrol_ucsf_env/watchlists/long/VEO/EPIC_ms/{0}.txt'.format(msid)
        if os.path.exists(text_file):
            with open(text_file,'r') as f:
                timepoints = f.readlines()
                timepoints = timepoints[::-1]
                for timepoint in timepoints:
                    mseid = timepoint.replace("\n","")
                    print("these are the mseID's", mseid)
                    create_flair_lesions(mseid, msid)

