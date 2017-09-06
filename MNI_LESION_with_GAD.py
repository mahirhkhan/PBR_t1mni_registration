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


"takes the difference between the two flair scans at different timepoints, multiplies the difference by the wm mask (created from sienax), create zscore image, multiplies that images by the lst lesion mask, and thresholds that image to get a new lesion mask" 


PBR_base_dir = '/data/henry7/PBR/subjects/'

class imageData():
    def __init__(self, lesion_MNI, wm_MNI, flair_file, t1_file):
        self.lesion_MNI = lesion_MNI
        self.wm_MNI = wm_MNI
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
    
    if os.path.exists(wm_MNI):
        print(wm_MNI)
        if not os.path.exists(mni_long):
            os.mkdir(mni_long)
        
        shutil.copyfile(wm_MNI,mni_long + "/wm_"+mseid + ".nii.gz")
        print(wm_MNI,mni_long + "/wm_"+mseid + ".nii.gz")

    if os.path.exists(lesion_MNI):
        print(lesion_MNI)
    
        if not os.path.exists(mni_long):
             os.mkdir(mni_long)
             print(mni_long)
        if not os.path.exists(mni_long+ "/lesion_"+mseid + ".nii.gz"):
            shutil.copyfile(lesion_MNI,mni_long + "/lesion_"+mseid + ".nii.gz")
            print(lesion_MNI,mni_long + "/lesion_"+mseid + ".nii.gz")
        flair_path = os.path.split(lesion_MNI)[0] +'/'+ os.path.split(flair_file)[-1]

        shutil.copyfile(flair_path, mni_long +'/'+ os.path.split(flair_path)[-1])
        print(flair_path, mni_long +'/'+ os.path.split(flair_path)[-1])

    return imageData(lesion_MNI, wm_MNI, flair_file, t1_file)
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


        flair_MNI = str(glob(mni_long + "ms*.nii.gz")[0])
        wm_MNI = str(glob(mni_long + "wm*.nii.gz")[0])
        lesion_MNI = str(glob(mni_long + "lesion_mse*.nii.gz")[0])
        cmd = ["fslmaths", lesion_MNI, "-bin", lesion_MNI.replace("lesion_", "lesion_bin_")]
        proc = Popen(cmd, stdout=PIPE)
        output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]
        lesion_bin_MNI = str(glob(mni_long + "lesion_bin_mse*.nii.gz")[0])
        if os.path.split(flair_file)[-1] == os.path.split(flair_MNI)[-1]:
            print("this is the flair file the lesion mask came from", flair_file)
            cmd = ["python", "/home/sf522915/PBR_t1mni_registration", "MNI_t1bl_new2.py", msid]
            proc = Popen(cmd, stdout=PIPE)
            output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]
        else:
            if os.path.exists(flair_file):
                maths = BinaryMaths()
                maths.inputs.operation= "sub"
                maths.inputs.in_file = flair_file
                maths.inputs.operand_file = flair_MNI
                maths.inputs.out_file = format_to_baseline_mni(flair_file,"_diff.nii.gz")
                print("your flair difference map is:",format_to_baseline_mni(flair_file,"_diff.nii.gz"))
                maths.cmdline
                maths.run()
        
                wm_diff = format_to_baseline_mni(flair_file,"_diff_WM.nii.gz")
                maths = BinaryMaths()
                maths.inputs.operation= "mul"
                maths.inputs.in_file = format_to_baseline_mni(flair_file,"_diff.nii.gz") 
                maths.inputs.operand_file = wm_MNI
                maths.inputs.out_file = wm_diff
                print("your flair difference WM map is:",format_to_baseline_mni(flair_file,"_diff_WM.nii.gz"))
                maths.cmdline
                maths.run()

                cmd = ["fslstats", wm_diff, "-S"]
                proc = Popen(cmd, stdout=PIPE)
                output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]
                std_dev = str(output).replace("[['", "")
                std_dev = std_dev.replace("]]", "").replace("'","")
                std_dev = float(std_dev)
                print(std_dev, "THIS IS THE STANDARD DEVIATION")

                cmd = ["fslstats", wm_diff, "-P", "50"]
                proc = Popen(cmd, stdout=PIPE)
                output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]
                median = str(output).replace("[['", "")
                median = median.replace("]]", "").replace("'","")
                median = float(median)
                print(median, "THIS IS THE MEDIAN")

                maths = BinaryMaths()
                maths.inputs.in_file = wm_diff
                maths.inputs.operation= "sub"
                maths.inputs.operand_value = median
                maths.inputs.out_file = wm_diff
                maths.cmdline
                maths.run()
                print(maths.cmdline)
    
                maths = BinaryMaths()
                maths.inputs.operation= "div"
                maths.inputs.in_file = wm_diff
                maths.inputs.operand_value = std_dev
                maths.inputs.out_file = wm_diff
                maths.cmdline
                maths.run()
                print(maths.cmdline)

                maths = BinaryMaths()
                maths.inputs.operation= "mul"
                maths.inputs.in_file = wm_diff
                maths.inputs.operand_value = -1 
                maths.inputs.out_file = wm_diff
                maths.cmdline
                maths.run()
                print(maths.cmdline)

                lesion_thr = format_to_baseline_mni(flair_file,"_lesion.nii.gz")
                maths = BinaryMaths()
                maths.inputs.operation= "mul"
                maths.inputs.in_file = lesion_bin_MNI
                maths.inputs.operand_file = wm_diff
                maths.inputs.out_file = lesion_thr
                maths.cmdline
                maths.run()
                print(maths.cmdline)

                thresh = Threshold()
                thresh.inputs.in_file = lesion_thr
                thresh.inputs.thresh = 0
                thresh.inputs.direction = 'above'
                thresh.inputs.out_file = lesion_thr
                thresh.cmdline
                thresh.run()

                cmd = ["fslmaths", lesion_thr, "-mul", "-1", "-bin", lesion_thr]
                proc = Popen(cmd, stdout=PIPE)
                output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]

                cmd = ["fslview", wm_diff, flair_MNI,flair_file, lesion_MNI, lesion_thr]
                proc = Popen(cmd, stdout=PIPE)
                output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]

def make_gad_mask(mseid): 
    if not os.path.exists(PBR_base_dir+"/"+mse+"/alignment/status.json"):
        run_pbr_align(mseid)
        with open(PBR_base_dir+"/"+mse+"/alignment/status.json") as data_file:  
            data = json.load(data_file)
            if len(data["gad_files"]) == 0:
                print("no {0} gad files".format(tp))
                gad_file ="none"
            else:
                gad_file = data["gad_files"][-1]
    if os.path.exists
     
           
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

 
    
