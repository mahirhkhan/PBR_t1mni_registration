import os
from glob import glob
from subprocess import Popen, PIPE
import json
from nipype.interfaces import fsl
from nipype.interfaces.fsl import RobustFOV, Reorient2Std
from nipype.interfaces.c3 import C3dAffineTool
import argparse
from getpass import getpass

PBR_base_dir = '/data/henry7/PBR/subjects'
password = getpass("mspacman password: ")
class imageData():
    def __init__(self, t1_file, t2_file, gad_file, flair_file, affines, bl_t1_mni):
        self.t1_file = t1_file
        self.t2_file = t2_file
        self.gad_file = gad_file
        self.flair_file = flair_file
        self.affines = affines
        self.bl_t1_mni = bl_t1_mni

def file_label(mse,tp="tpX",count=1):
    if not os.path.exists(PBR_base_dir+"/"+mse+"/alignment/status.json"):
        run_pbr_align(mseid)
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
    if t1_file == "none": #or t2_file == "none":
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
       if not os.path.exists(affine):
           print("NO AFFINES TO CONVERT - skipping this subject")
       else:
           print ("Converting the following affine from .txt to .mat format...")
           print (affine)
           cmd = ["c3d_affine_tool", "-itk", affine, "-o", affine.split(".")[0]+ ".mat"]
           proc = Popen(cmd, stdout=PIPE)
           proc.wait()
           print ("Conversion complete"); print

def conv_xfm(affines,TP1_base_dir):
    for affine in affines:
        if not os.path.exists(affine):
           print("NO AFFINES TO CONVERT - skipping this subject")
        else:
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
    if os.path.exists(format_to_baseline_mni(in_file,"_T1mni.nii.gz")):
        print("FLIRT had been run for:",in_file)
    else: 
        if not os.path.exists(in_file):
            print(in_file, "this file does not exist")
        else:
            in_matrix = format_to_baseline_mni(in_file,"_affine_mni.mat")
            print ("Applying FLIRT to the following file...")
            print (in_file)
            flt = fsl.FLIRT()
            flt.inputs.cost = "mutualinfo"
            flt.inputs.in_file = in_file
            flt.inputs.reference = bl_t1_mni 
            flt.inputs.output_type = "NIFTI_GZ"
            flt.inputs.in_matrix_file = in_matrix
            flt.inputs.out_file = format_to_baseline_mni(in_file,"_T1mni.nii.gz")
            flt.cmdline
            flt.run()
            print ("FLIRT complete"); print()
            print (in_file, "FLIRT complete"); print

def apply_t1_flirt(in_file, bl_t1_mni):
    if os.path.exists(format_to_baseline_mni(in_file,"_T1mni.nii.gz")):
        print("FLIRT had been run for:",in_file)
    else: 
        in_matrix = os.path.split(bl_t1_mni)[0] + "/affine.mat"
        flt = fsl.FLIRT()
        flt.inputs.cost = "mutualinfo"
        flt.inputs.in_file = in_file
        flt.inputs.reference = bl_t1_mni 
        flt.inputs.output_type = "NIFTI_GZ"
        flt.inputs.in_matrix_file = in_matrix
        flt.inputs.out_file = format_to_baseline_mni(in_file,"_T1mni.nii.gz")
        flt.cmdline
        flt.run()
        print ("FLIRT complete"); print()
        print (in_file, "FLIRT complete"); print

def run_pbr_align(mseid):
    #from getpass import getpass
    alignment_folder = "/data/henry7/PBR/subjects/{0}/alignment".format(mseid)
    if os.path.exists(alignment_folder):
        cmd_rm = ['rm','-r', alignment_folder]
        print (cmd_rm)
        proc = Popen(cmd_rm)
        proc.wait()
    
    #password = getpass("mspacman password: ")
    cmd = ['pbr', mseid, '-w', 'align', '-R', "-ps", password]
    print (cmd)
    proc = Popen(cmd)
    proc.wait()
   
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

def sub_gad_nogad(gad_file, t1_file):
    gad_mni = os.path.split(gad_file)[0] +"/baseline_mni/"+ os.path.split(gad_file)[-1].replace(".nii.gz","_T1mni.nii.gz")
    t1_mni = os.path.split(t1_file)[0] +"/baseline_mni/"+ os.path.split(t1_file)[-1].replace(".nii.gz","_T1mni.nii.gz")
    if os.path.exists(gad_mni):
        if os.path.exists(t1_mni):
            from nipype.interfaces.fsl import BinaryMaths
            gad_f = os.path.split(gad_file)[-1].replace(".nii.gz", "")
            t = os.path.split(t1_file)[-1]
            t1_f = t.split('-')[2] +'-'+ t.split('-')[3].replace(".nii.gz", "_diff_map.nii.gz")
            out_file = os.path.split(t1_file)[0] +"/baseline_mni/"+ gad_f +"_"+ t1_f
            maths = BinaryMaths()
            maths.inputs.operation= "sub"
            maths.inputs.in_file = gad_mni
            maths.inputs.operand_file = t1_mni
            maths.inputs.out_file = out_file
            print("your GAD difference map is:", out_file)
            maths.cmdline
            maths.run()
    else:
        print("did not have GAD file to produce difference map")

def check_for_trans_file(mse_id):
    nii_folder = '/data/henry7/PBR/subjects/{}/nii'.format(mse_id)
    #print(nii_folder)
    trans_file = glob('/data/henry7/PBR/subjects/{}/alignment/mni_angulated/*_trans.nii.gz'.format(mse_id))
    print(trans_file)
    jim_roi = glob(nii_folder + '/*.roi')
    if not (len(trans_file) > 0):
        print('deleting alignment folder due to lack of trans file')
        if (len(jim_roi) > 0):
            os.system('mkdir {}/tca_roi'.format(nii_folder))
            os.system('mv {}/*.hdr {}/tca_roi'.format(nii_folder, nii_folder))
            os.system('mv {}/*.img {}/tca_roi'.format(nii_folder, nii_folder))
            os.system('mv {}/*.roi {}/tca_roi'.format(nii_folder, nii_folder))
            os.system('rm -r /data/henry7/PBR/subjects/{}/alignment'.format(mse_id))
        else:
            os.system('rm -r /data/henry7/PBR/subjects/{}/alignment'.format(mse_id))
    else:
        print('trans file exists in baseline')
        print(trans_file)

def lesion_mask(mseid,bl_t1_mni):
    lst_mask = glob("/data/henry7/PBR/subjects/{0}/mindcontrol/*{0}*FLAIR*/lst/lst_edits/no_FP_filled_FN*.nii.gz".format(mseid))
    if len(lst_mask) > 0:
        lst_file = lst_mask[0]
        apply_t1_flirt(lst_file,bl_t1_mni)
        print ('lst file has been registered to T1 MNI space'); print ()
    else:
        print ('No lesion mask to register, moving on...')
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
        apply_t1_flirt(tp1.t1_file, tp1.bl_t1_mni)
        apply_flirt(tp1.t2_file, tp1.bl_t1_mni)
        apply_flirt(tp1.gad_file, tp1.bl_t1_mni)
        apply_flirt(tp1.flair_file, tp1.bl_t1_mni)
        sub_gad_nogad(tp1.gad_file, tp1.t1_file)
        lesion_mask(info[1],tp1.bl_t1_mni)
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
        apply_t1_flirt(tp2.t1_file, tp1.bl_t1_mni)
        apply_flirt(tp2.t2_file, tp1.bl_t1_mni)
        apply_flirt(tp2.gad_file, tp1.bl_t1_mni)
        apply_flirt(tp2.flair_file, tp1.bl_t1_mni)
        sub_gad_nogad(tp2.gad_file, tp2.t1_file)
        lesion_mask(info[2],tp1.bl_t1_mni)

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
                check_for_trans_file(baseline_mse)
                for timepoint in timepoints:
                    mse_bl = timepoints[0].replace("\n","")
                    mseid = timepoint.replace("\n","")
                    print("the mse's in this workflow are:", timepoint)
                    info = [msid, mse_bl, mseid]
                    align_to_baseline(info)
                    print ("{}'s T1MNI registration complete".format(mseid)) 
            print ("{0}'s longitudinal registration complete".format(msid))
        else:
            print ("no msid tracking txt file exists")
            info = False
            continue
       

