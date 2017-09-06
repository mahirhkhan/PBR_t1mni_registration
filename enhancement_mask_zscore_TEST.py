import os
from glob import glob
import subprocess 
from subprocess import Popen, PIPE
import json
from nipype.interfaces import fsl
from nipype.interfaces.fsl import RobustFOV, Reorient2Std
from nipype.interfaces.c3 import C3dAffineTool
import argparse
from getpass import getpass
from nipype.interfaces.fsl import BinaryMaths, UnaryMaths, ErodeImage, ImageStats, Threshold, DilateImage


PBR_base_dir = '/data/henry7/PBR/subjects/'

password = getpass("mspacman password: ")

def get_tps(msid,mseid):
    filepath = '/data/henry6/mindcontrol_ucsf_env/watchlists/long/VEO/EPIC_ms/{0}.txt'.format(msid)
    if os.path.exists(filepath):
        with open(filepath,'r') as f:
            timepoints = f.readlines()
            mse_bl = timepoints[0].replace("\n","")
            info = [msid, mse_bl, mseid]
            return info
    else:
        print ("no msid tracking txt file exists")
        return False

class imageData():
    def __init__(self, t1_file, gad_file, bl_t1_mni):
        self.t1_file = t1_file
        self.gad_file = gad_file
        self.bl_t1_mni = bl_t1_mni

def run_pbr_align(mseid):
    alignment_folder = "/data/henry7/PBR/subjects/{0}/alignment".format(mseid)
    if os.path.exists(alignment_folder):
        cmd_rm = ['rm','-r', alignment_folder]
        print (cmd_rm)
        proc = Popen(cmd_rm)
        proc.wait()
    cmd = ['pbr', mseid, '-w', 'align', '-R', "-ps", password]
    print (cmd)
    proc = Popen(cmd)
    proc.wait()

def file_label(mse,tp="tpX",count=1):
    if not os.path.exists(PBR_base_dir+"/"+mse+"/alignment/status.json"):
        run_pbr_align(mseid)
    with open(PBR_base_dir+"/"+mse+"/alignment/status.json") as data_file:  
        data = json.load(data_file)
        #checking alignment status file for t1 and gad 
        if len(data["t1_files"]) == 0:
            print("no {0} t1 files".format(tp))
            run_pbr_align(mseid)
            t1_file = "none"
        else:
            t1_file = data["t1_files"][-1]
            bl_t1_mni = PBR_base_dir+'/'+mse +"/alignment/mni_angulated/"+os.path.split(t1_file)[-1].replace(".nii.gz", "_trans.nii.gz")
            
        if len(data["gad_files"]) == 0:
            print("no {0} gad files".format(tp))
            gad_file ="none"
        else:
            gad_file = data["gad_files"][-1]

     
    if t1_file == "none":
        if count > 3:
            print ("Error in status.json file, T1 not being categorized correctly")
        else:
            count += 1
            file_label(mse,tp,count)
    else:
        return imageData(t1_file, gad_file, bl_t1_mni)

def sub_gad_nogad(gad_file, t1_file, mseid):
    gad_mni = os.path.split(gad_file)[0] +"/baseline_mni/"+ os.path.split(gad_file)[-1].replace(".nii.gz","_T1mni.nii.gz")
    t1_mni = os.path.split(t1_file)[0] +"/baseline_mni/"+ os.path.split(t1_file)[-1].replace(".nii.gz","_T1mni.nii.gz")
    if os.path.exists(gad_mni):
        if os.path.exists(t1_mni):
            if not os.path.exists("/data/henry7/PBR/subjects/"+ mseid+ "/enhancement_mask"):
                 os.mkdir("/data/henry7/PBR/subjects/"+ mseid+ "/enhancement_mask/")
            gad_f = os.path.split(gad_file)[-1].replace(".nii.gz", "")
            t = os.path.split(t1_file)[-1]
            t1_f = t.split('-')[2] +'-'+ t.split('-')[3].replace(".nii.gz", "_diff_map.nii.gz")
            out_file = "/data/henry7/PBR/subjects/"+ mseid+ "/enhancement_mask/" +  gad_f +"_"+ t1_f

            # gad - no gad 
            maths = BinaryMaths()
            maths.inputs.operation= "sub"
            maths.inputs.in_file = gad_mni
            maths.inputs.operand_file = t1_mni
            maths.inputs.out_file = out_file
            print("your GAD difference map is:", out_file)
            maths.cmdline
            maths.run()
            
            #diff div pre gad 
            out_file_new = out_file 
            maths = BinaryMaths()
            maths.inputs.operation= "div"
            maths.inputs.in_file = out_file_new
            maths.inputs.operand_file = t1_mni
            out_file_div = out_file_new.replace("_diff_map.nii.gz", ("_divT1.nii.gz"))
            maths.inputs.out_file = out_file_div
            print("your GAD difference map divided by T1 is:", out_file_div)
            maths.cmdline
            maths.run()

            #invert diff/pre image	
            final_diff =  out_file_div.replace("_divT1.nii.gz", ("_divT1_inv.nii.gz"))
            cmd = ["fslmaths", out_file_div, "-mul", "-1", final_diff]
            proc = Popen(cmd, stdout=PIPE)
            output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]	
            print("your GAD difference map divided by T1 inverted is:",out_file_div.replace("_divT1.nii.gz", ("_divT1_inv.nii.gz")))
            return final_diff
            
    else:
        print("did not have GAD file to produce difference map")
        return False


def check_mni_angulated_folder(mseid):
    filepath = '/data/henry7/PBR/subjects/{0}/alignment/mni_angulated'.format(mseid)
    if os.path.exists(filepath):
        print ("mni_angulated folder for {0} exists".format(mseid))
        check = True
    else:
        print ("mni_angulated folder for {0} does not exist, fixing the issue".format(mseid))
        run_pbr_align(mseid)
        print ("mni_angulated folder for {0} exists".format(mseid))
        check = False
    return check


def gad_mask(mseid, msid):
    mni_long = PBR_base_dir + msid + "/MNI/"
    wm_mask = str(glob(mni_long + "wm*.nii.gz")[0])
    gad_dir = PBR_base_dir +'/'+  mseid+ '/enhancement_mask/'
    if os.path.exists(gad_dir):
        diff_map = str(glob(gad_dir + "*inv.nii.gz")[0])
        if os.path.exists(wm_mask):
            print(wm_mask, "THIS MASK EXISTS")
   
            # multiply the wm mask by the gad difference map          
            maths = BinaryMaths()
            maths.inputs.operation= "mul"
            maths.inputs.in_file = wm_mask
            maths.inputs.operand_file = diff_map
            final_wm = PBR_base_dir + mseid+ '/enhancement_mask/wm_diff.nii.gz'
            maths.inputs.out_file = final_wm 
            maths.cmdline
            maths.run()
   
            #create the zscore map           
            cmd = ["fslstats", final_wm, "-S"]
            proc = Popen(cmd, stdout=PIPE)
            output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]
            std_dev = str(output).replace("[['", "")
            std_dev = float((std_dev.replace("]]", "").replace("'","")))
            print(std_dev, "THIS IS THE STANDARD DEVIATION")

            cmd = ["fslstats", final_wm, "-P", "50"]
            proc = Popen(cmd, stdout=PIPE)
            output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]
            median = str(output).replace("[['", "")
            median = float(median.replace("]]", "").replace("'",""))
            print(median, "THIS IS THE MEDIAN")
            

            maths = BinaryMaths()
            maths.inputs.in_file = final_wm
            maths.inputs.operation= "sub"
            maths.inputs.operand_value = median
            maths.inputs.out_file =  PBR_base_dir + mseid+ '/enhancement_mask/wm_zscore.nii.gz'
            maths.cmdline
            maths.run()
            print(maths.cmdline)

            maths = BinaryMaths()
            maths.inputs.operation= "div"
            maths.inputs.in_file = PBR_base_dir + mseid+ '/enhancement_mask/wm_zscore.nii.gz'
            maths.inputs.operand_value = std_dev
            maths.inputs.out_file =  PBR_base_dir + mseid+ '/enhancement_mask/wm_zscore.nii.gz'
            maths.cmdline
            maths.run()
            print(maths.cmdline)

            """maths = BinaryMaths()
            maths.inputs.operation= "mul"
            maths.inputs.in_file = PBR_base_dir + mseid+ '/enhancement_mask/wm_zscore.nii.gz'
            maths.inputs.operand_file = wm_mask #PBR_base_dir + mseid+'/enhancement_mask/wm_MNI.nii.gz'
            maths.inputs.out_file = PBR_base_dir + mseid+ '/enhancement_mask/wm_zscore.nii.gz'
            maths.cmdline
            maths.run()
            print(maths.cmdline)

            maths = BinaryMaths()
            maths.inputs.operation= "mul"
            maths.inputs.in_file = PBR_base_dir + mseid+ '/enhancement_mask/wm_zscore.nii.gz'
            maths.inputs.operand_value = -1 
            maths.inputs.out_file = PBR_base_dir + mseid+ '/enhancement_mask/wm_zscore.nii.gz'
            maths.cmdline
            maths.run()
            print(maths.cmdline)"""
            
            mni_long = "/data/henry7/PBR/subjects/" + msid + "/MNI/"
            lesion_mask = str(glob(mni_long + "lesion_bin_mse*.nii.gz")[0])
            print(lesion_mask, "THIS IS THE LESION MASK")

            maths = BinaryMaths()
            maths.inputs.operation= "mul"
            maths.inputs.in_file = PBR_base_dir + mseid+ '/enhancement_mask/wm_zscore.nii.gz'
            maths.inputs.operand_file = lesion_mask
            maths.inputs.out_file = PBR_base_dir + mseid+ '/enhancement_mask/wm_zscore.nii.gz'
            maths.cmdline
            maths.run()
            print(maths.cmdline)

            
            thresh = Threshold()
            thresh.inputs.in_file = PBR_base_dir + mseid+ '/enhancement_mask/wm_zscore.nii.gz'
            thresh.inputs.thresh = .5
            thresh.inputs.direction = 'below'
            thresh.inputs.out_file =  PBR_base_dir + mseid + '/enhancement_mask/gad_mask_zscore5.nii.gz'
            thresh.cmdline
            thresh.run()
            """
            erode = ErodeImage()
            erode.inputs.kernel_shape = "gauss" 
            erode.inputs.kernel_size = 1.5
            erode.inputs.in_file = PBR_base_dir + mseid + '/enhancement_mask/gad_mask_zscore5.nii.gz'
            erode.inputs.out_file = PBR_base_dir + mseid + '/enhancement_mask/gad_mask_zscore5.nii.gz'
            erode.cmdline
            erode.run()
            print(erode.cmdline)

            dil = DilateImage()
            dil.inputs.kernel_shape = "boxv" 
            dil.inputs.operation = "mean"
            dil.inputs.kernel_size = 1  
            dil.inputs.in_file = PBR_base_dir + mseid + '/enhancement_mask/gad_mask_zscore5.nii.gz'
            dil.inputs.out_file = PBR_base_dir + mseid + '/enhancement_mask/gad_mask_zscore5.nii.gz'
            dil.cmdline
            dil.run()
            """


def create_gad_enhancement(info):
    #1) check if TP1 has mni_angulated folder, even if TP1 = TPx
 
    check_mni_angulated_folder(info[1])
   
    #2) check if TP1 has /baseline_mni folder
    
    tp1_base_dir = '/data/henry7/PBR/subjects/{0}/alignment'.format(info[1])
    tp2_base_dir = '/data/henry7/PBR/subjects/{0}/alignment'.format(info[2])
    tp1 = file_label(info[1],tp="BL")
    #3) check if TP1 = TPx
    if info[1] == info[2]:
        print ('{0} is TP1'.format(info[2])); print()
        #tp1 = file_label(info[1],tp="BL")
        sub_gad_nogad(tp1.gad_file, tp1.t1_file, mseid)
        print(tp1.gad_file, tp1.t1_file, mseid);
        #create_wm_mask(msid, mseid, tp1.t1_file)
        gad_mask(mseid, msid)
       
    else:
        tp2 = file_label(info[2])
        sub_gad_nogad(tp2.gad_file, tp2.t1_file, mseid)
        print(tp2.gad_file, tp2.t1_file, mseid)
        #create_wm_mask(msid, mseid, tp1.t1_file)
        gad_mask(mseid, msid)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('ms', nargs="+")
    args = parser.parse_args()
    ms = args.ms
    #outdir = cc["output_directory"]
    print("msid is:", ms)

    for msid in ms:
        text_file = '/data/henry6/mindcontrol_ucsf_env/watchlists/long/VEO/EPIC_ms/{0}.txt'.format(msid)
        if os.path.exists(text_file):
            with open(text_file,'r') as f:
                timepoints = f.readlines()
                baseline_mse = timepoints[0].replace("\n","")
                for timepoint in timepoints:
                    mse_bl = timepoints[0].replace("\n","")
                    mseid = timepoint.replace("\n","")
                    info = [msid, mse_bl, mseid]
                    create_gad_enhancement(info)
                    print()
                    print ("{}'s GAD ENHANCMENT map complete".format(mseid)) 
            print ("Gad Difference map complete".format(msid))
        else:
            print ("no msid tracking txt file exists")
            info = False
            continue
       


