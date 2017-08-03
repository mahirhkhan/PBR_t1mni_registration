
# coding: utf-8

# In[8]:

import os
from subprocess import Popen, PIPE
import json
from nipype.interfaces import fsl
from nipype.interfaces.fsl import RobustFOV, Reorient2Std
from nipype.interfaces.c3 import C3dAffineTool
import argparse

PBR_base_dir = '/data/henry7/PBR/subjects'

class imageData():
    def __init__(self, t1_file, t2_file, gad_file, flair_file, affines, bl_t1_mni):
        self.t1_file = t1_file
        self.t2_file = t2_file
        self.gad_file = gad_file
        self.flair_file = flair_file
        self.affines = affines
        self.bl_t1_mni = bl_t1_mni

def file_label(mse,tp="tpX",count=1):
    with open(PBR_base_dir+"/"+mse+"/alignment/status.json") as data_file:  
        data = json.load(data_file)
        
        #checking alignment status file for t1, t2, gad and flair 
        if len(data["t1_files"]) == 0:
            print("no {0} t1 files".format(tp))
            run_pbr_align(mseid)
            t1_file = "none"
        else:
            t1_file = data["t1_files"][-1]
            bl_t1_mni = PBR_base_dir+'/'+mse +"/alignment/mni_angulated/"+os.path.split(t1_file)[-1].replace(".nii.gz", "_trans.nii.gz")
        
        if len(data["t2_files"]) == 0:
            print("no {0} t2 files".format(tp))
            run_pbr_align(mseid)
            t2_file = "none"
        else:
            t2_file = data["t2_files"][-1]
            
        if len(data["gad_files"]) == 0:
            print("no {0} gad files".format(tp))
            gad_file ="none"
        else:
            gad_file = data["gad_files"][-1]
     
        if len(data["flair_files"]) == 0:
            print("no {0} flair files".format(tp))
            flair_file = "none"
        else:
            flair_file = data["flair_files"][-1]
            
        if len(data["affines"]) == 0:
            print("no {0} affines".format(tp))
            affines = "none"
        else:
            affines = data["affines"]
    
    #run program again if t1_file = "none" or t2_file = "none", but only run 2 iterations of run_pbr_align to avoid recursive errors
    if t1_file == "none" or t2_file == "none":
        if count > 3:
            print ("Error in status.json file, T1 or T2 files are not being categorized correctly")
            #write error script
        else:
            count += 1
            file_label(mse,tp,count)
    else:
        return imageData(t1_file, t2_file, gad_file, flair_file, affines, bl_t1_mni)

def conv_aff_mni(t1_mni_mat):
    cmd = ["c3d_affine_tool", "-itk", t1_mni_mat, "-o", t1_mni_mat.split(".")[0]+ ".mat"]
    proc = Popen(cmd, stdout=PIPE)
    global t1_mat
    t1_mat = t1_mni_mat.replace(".txt", ".mat")
    return t1_mat
    print(cmd)

def conv_aff(affines):
    for affine in affines:
        print ("Converting the following affine from .txt to .mat format...")
        print (affine)
        cmd = ["c3d_affine_tool", "-itk", affine, "-o", affine.split(".")[0]+ ".mat"]
        proc = Popen(cmd, stdout=PIPE)
        proc.wait()
        print ("Conversion complete"); print()

def conv_xfm(affines,TP1_base_dir):
    for affine in affines:
        print ("Transforming the following affine to TP1 T1MNI space...")
        print (affine)
        invt = fsl.ConvertXFM()
        invt.inputs.in_file = affine.split(".")[0]+ ".mat"
        invt.inputs.in_file2 = TP1_base_dir + "/mni_angulated/affine.mat"
        invt.inputs.concat_xfm = True
        invt.inputs.out_file = format_to_baseline_mni(affine,"_mni.mat")
        invt.cmdline
        invt.run()
        print ("Transformation complete"); print()

def apply_flirt(in_file, bl_t1_mni):
    if not os.path.exists(format_to_baseline_mni(in_file,"_affine_mni.mat","hide")):
        print ("No matrix file exists for this file, could not perform FLIRT")
        print (in_file)
    else:
        print ("Applying FLIRT to the following file...")
        print (in_file)
        flt = fsl.FLIRT()
        flt.inputs.cost = "mutualinfo"
        flt.inputs.in_file = in_file
        flt.inputs.reference = bl_t1_mni 
        flt.inputs.output_type = "NIFTI_GZ"
        flt.inputs.in_matrix_file = format_to_baseline_mni(in_file,"_affine_mni.mat")
        flt.inputs.out_file = format_to_baseline_mni(in_file,"_T1mni.nii.gz")
        flt.cmdline
        flt.run()
        print ("FLIRT complete"); print()

def run_pbr_mni_angulated(mseid):
    cmd = ['pbr', mseid, '-w', 'alignment', '-R']
    print (cmd)
    proc = Popen(cmd)
    proc.wait()
    
def run_pbr_align(mseid):
    alignment_folder = "/data/henry7/PBR/subjects/{0}/alignment".format(mseid)
    cmd = ['rm', alignment_folder]
    print (cmd)
    proc = Popen(cmd)
    proc.wait()
    cmd = ['pbr', mseid, '-w', 'align', '-R']
    print (cmd)
    proc = Popen(cmd)
    proc.wait()
    run_pbr_mni_angulated(mseid)

def check_mni_angulated_folder(mseid):
    filepath = '/data/henry7/PBR/subjects/{0}/alignment/mni_angulated'.format(mseid)
    if os.path.exists(filepath):
        print ("mni_angulated folder for {0} exists".format(mseid))
        check = True
    else:
        print ("mni_angulated folder for {0} does not exist, fixing the issue".format(mseid))
        run_pbr_mni_angulated(mseid)
        print ("mni_angulated folder for {0} exists".format(mseid))
        check = False
    return check

def format_to_baseline_mni(in_file,extension,message="show"):
    out_path = in_file.split("alignment")[0] + "alignment/baseline_mni"
    file_name = in_file.split('/')[-1].split('.')[0] + extension
    if not os.path.exists(out_path):
        os.makedirs(out_path)
    out_file = os.path.join(out_path, file_name)
    if message == "show":
        print ("Your output file will be: {0}".format(out_file))
    return out_file

def get_msid(mseid):
    from glob import glob
    if check_mni_angulated_folder(mseid) is True:
        files = glob("/data/henry7/PBR/subjects/{0}/alignment/mni_angulated/ms*".format(mseid))
        msid = files[0].split('/')[-1].split('-')[0]
        mseid = files[0].split('/')[-1].split('-')[1]
        return msid
    else:
        return 1

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

def align_to_baseline(info):
    #1) check if TP1 has mni_angulated folder, even if TP1 = TPx
    
    check_mni_angulated_folder(info[1])
    
    #2) check if TP1 has /baseline_mni folder
    
    tp1_base_dir = '/data/henry7/PBR/subjects/{0}/alignment'.format(info[1])
    tp2_base_dir = '/data/henry7/PBR/subjects/{0}/alignment'.format(info[2])
    
    t1_mni_mat = tp1_base_dir+"/mni_angulated/affine.txt"
    conv_aff_mni(t1_mni_mat)
    
    tp1 = file_label(info[1],tp="BL")
    
    if not os.path.exists(os.path.join(tp1_base_dir,"baseline_mni")):
        #align TP1's T2/lesion/FLAIR/etc to T1MNI space
        conv_aff(tp1.affines)
        conv_xfm(tp1.affines, tp1_base_dir)
        apply_flirt(tp1.t2_file, tp1.bl_t1_mni)
    else:
        print ("Baseline already has files in T1MNI space, skipping this step"); print()
        
    #3) check if TP1 = TPx

    if info[1] == info[2]:
        print ('No need to apply additional alignment, {0} is TP1'.format(info[2])); print()
    else:
        print ('{0} will need additional alignment'.format(info[2]))
        tp2 = file_label(info[2])
        conv_aff(tp2.affines)
        conv_xfm(tp2.affines, tp1_base_dir)
        apply_flirt(tp2.t1_file, tp1.bl_t1_mni)
        apply_flirt(tp2.t2_file, tp1.bl_t1_mni)
    

#call functions
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
                for timepoint in timepoints:
                    mse_bl = timepoints[0].replace("\n","")
                    mseid = timepoint.replace("\n","")
                    info = [msid, mse_bl, mseid]
                    align_to_baseline(info)
                    print ("{}'s T1MNI registration complete".format(mseid)) 
            print ("{0}'s longitudinal registration complete".format(msid))
        else:
            print ("no msid tracking txt file exists")
            info = False
            continue
       


# In[10]:




# success: mse4334 (tp2.t1_file error)
# fail: mse3046 (no tracking txt file)
