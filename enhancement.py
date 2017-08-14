import os
from glob import glob
from subprocess import Popen, PIPE
import json
from nipype.interfaces import fsl
from nipype.interfaces.fsl import RobustFOV, Reorient2Std
from nipype.interfaces.c3 import C3dAffineTool
import argparse
from getpass import getpass
from nipype.interfaces.fsl import BinaryMaths, UnaryMaths, ErodeImage, ImageStats, Threshold


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
            maths = BinaryMaths()
            maths.inputs.operation ="mul"
            maths.inputs.operand_value = -1
            maths.inputs.in_file = out_file_div
            final_diff =  out_file_div.replace("_divT1.nii.gz", ("_divT1_inv.nii.gz"))
            maths.inputs.out_file = final_diff
            print("your GAD difference map divided by T1 inverted is:",out_file_div.replace("_divT1.nii.gz", ("_divT1_inv.nii.gz")))
            maths.cmdline
            maths.run()
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

def create_wm_mask(msid, mseid, t1_file):
    sienax_base_dir = "/data/pelletier1/genentech/sienax_yr89_lst_lesions/"
    gad_base_dir = PBR_base_dir + mseid + "/enhancement_mask/"
    msid_new = "ms" + msid.replace("ms","").zfill(4)
    bl_t1 = os.path.split(t1_file)[0] +"/baseline_mni/"+ os.path.split(t1_file)[-1].replace(".nii.gz","_T1mni.nii.gz")
    for sienax in os.listdir(sienax_base_dir):
        if sienax.startswith(msid_new):
            wm_mask = sienax_base_dir + sienax + "/I_stdmaskbrain_pve_2.nii.gz"
            lesion_mask = sienax_base_dir + sienax + "/lesion_mask.nii.gz"
            print(wm_mask, lesion_mask, msid_new, mseid)
            
            maths = BinaryMaths()
            maths.inputs.operation= "add"
            maths.inputs.in_file = wm_mask 
            maths.inputs.operand_file = lesion_mask
            if not os.path.exists(gad_base_dir):
                os.mkdir(gad_base_dir)
            wm = gad_base_dir + "/wm_mask.nii.gz"
            maths.inputs.out_file = wm  
            maths.cmdline
            maths.run()
            umaths = UnaryMaths()
            umaths.inputs.operation= "bin"
            umaths.inputs.in_file = wm
            umaths.inputs.out_file = wm  
            umaths.cmdline
            umaths.run()

            flt = fsl.FLIRT()
            flt.inputs.interp = "nearestneighbour"
            flt.inputs.dof = 6 
            flt.inputs.in_file = wm
            flt.inputs.reference = bl_t1 
            flt.inputs.output_type = "NIFTI_GZ"
            flt.inputs.out_file = gad_base_dir + "wm_MNI.nii.gz"
            flt.cmdline
            flt.run()
            print(flt.cmdline)
            """
            flt = fsl.FLIRT()
            flt.inputs.interp = "nearestneighbour"
            flt.inputs.dof = 6 
            flt.inputs.in_file = lesion_mask
            flt.inputs.reference = bl_t1 
            flt.inputs.output_type = "NIFTI_GZ"
            flt.inputs.out_file = gad_base_dir + "lesion_MNI.nii.gz"
            flt.cmdline
            flt.run()
            print(flt.cmdline)
            """

            erode = ErodeImage()
            erode.inputs.kernel_shape = "2D" 
            wm_MNI = gad_base_dir + "/wm_MNI.nii.gz" 
            erode.inputs.in_file = wm_MNI 
            erode.inputs.out_file = wm_MNI
            erode.cmdline
            erode.run()
            return wm_MNI

def gad_mask(mseid):
    for files in os.listdir(PBR_base_dir +mseid +'/enhancement_mask/'):
        gad_dir = PBR_base_dir +  mseid+ '/enhancement_mask/'
        if files.endswith("inv.nii.gz"):
            diff_map = gad_dir + files
            maths = BinaryMaths()
            maths.inputs.operation= "mul"
            if not os.path.exists(PBR_base_dir + mseid+ '/enhancement_mask/wm_MNI.nii.gz'):
                continue
            maths.inputs.in_file = PBR_base_dir + mseid+ '/enhancement_mask/wm_MNI.nii.gz'
            maths.inputs.operand_file = diff_map
            final_wm = PBR_base_dir + mseid+ '/enhancement_mask/wm_diff.nii.gz'
            maths.inputs.out_file = final_wm 
            maths.cmdline
            maths.run()
            
            cmd = ["fslstats", final_wm, "-P", "3"]
            proc = Popen(cmd, stdout=PIPE)
            output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]
            thr = str(output).replace("[['", "")
            thr = float(thr.replace("]]", "").replace("'",""))
            print(thr, "THIS IS THE THRESHOLD")
            
            thresh = Threshold()
            thresh.inputs.in_file = final_wm 
            thresh.inputs.thresh = thr
            thresh.inputs.direction = 'above'
            thresh.inputs.out_file =  PBR_base_dir + mseid + '/enhancement_mask/gad_mask.nii.gz'
            thresh.cmdline
            thresh.run()
            print("THIS IS YOUR FINAL GAD MASK:",PBR_base_dir + mseid + '/enhancement_mask/gad_mask.nii.gz' )
            
            erode = ErodeImage()
            erode.inputs.kernel_shape = "2D" 
            erode.inputs.in_file = PBR_base_dir + mseid + '/enhancement_mask/gad_mask.nii.gz' 
            erode.inputs.out_file = PBR_base_dir + mseid + '/enhancement_mask/gad_mask_ero.nii.gz'
            erode.cmdline
            erode.run()
 
            
    
    



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
        create_wm_mask(msid, mseid, tp1.t1_file)
        gad_mask(mseid)
       
    else:
        tp2 = file_label(info[2])
        sub_gad_nogad(tp2.gad_file, tp2.t1_file, mseid)
        print(tp2.gad_file, tp2.t1_file, mseid)
        create_wm_mask(msid, mseid, tp1.t1_file)
        gad_mask(mseid)

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
       


