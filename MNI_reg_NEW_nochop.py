import os
from glob import glob
from subprocess import Popen, PIPE
import json
from nipype.interfaces import fsl
from nipype.interfaces.fsl import RobustFOV, Reorient2Std
from nipype.interfaces.c3 import C3dAffineTool
import argparse
from getpass import getpass
import shutil

PBR_base_dir = '/data/henry7/PBR/subjects'
password = getpass("mspacman password: ")
class imageData():
    def __init__(self, t1_file, t2_file, gad_file, flair_file, affines, bl_t1_mni, lst_file):
        self.t1_file = t1_file
        self.t2_file = t2_file
        self.gad_file = gad_file
        self.flair_file = flair_file
        self.affines = affines
        self.bl_t1_mni = bl_t1_mni
        self.lst_file = lst_file


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
        lst_mask = glob("/data/henry7/PBR/subjects/{0}/mindcontrol/*{0}*FLAIR*/lst/lst_edits/no_FP_filled_FN*.nii.gz".format(mseid))
        if len(lst_mask) == 0:
            lst_file = "none"
        else:
            lst_file = lst_mask[0]
            #return ImageData(lst_file)


    #run program again if t1_file = "none" or t2_file = "none", but only run 2 iterations of run_pbr_align to avoid recursive errors
    if t1_file == "none": #or t2_file == "none":
        if count > 3:
            print ("Error in status.json file, T1 or T2 files are not being categorized correctly")
            #write error script
        else:
            count += 1
            file_label(mse,tp,count)
    else:
        return imageData(t1_file, t2_file, gad_file, flair_file, affines, bl_t1_mni, lst_file)


def copy_mni_bl(bl_t1_mni):
    mni_angulated = os.path.split(bl_t1_mni)[0]
    baseline_mni = os.path.split(mni_angulated)[0] + "/baseline_mni/"
    if not os.path.exists(os.path.split(mni_angulated)[0] + "/baseline_mni/"):
        os.mkdir(os.path.split(mni_angulated)[0] + "/baseline_mni/")
    if os.path.exists(bl_t1_mni):

        for item in os.listdir(mni_angulated):
            if item.endswith(".nii.gz"):
                if not "flirt" in item:
                    new_name = item.replace("trans", "T1mni")
                    shutil.copyfile(mni_angulated +"/"+ item, baseline_mni +"/"+ new_name)
                    print(mni_angulated +"/"+ item, baseline_mni +"/"+ new_name)

def create_affine_tp1(in_file, bl_t1_mni):
    if in_file.endswith(".nii.gz"):
        flt = fsl.FLIRT()
        flt.inputs.in_file = in_file
        flt.inputs.reference = bl_t1_mni
        flt.inputs.output_type = "NIFTI_GZ"
        flt.inputs.out_matrix_file = os.path.split(in_file)[0] + "/mni_affine.mat"
        flt.inputs.interp = "nearestneighbour"
        flt.inputs.dof = 6
        flt.cmdline
        flt.run()
        print(flt.cmdline, "FINISHED CREATING AFFINE MATRIX FOR TP1")

##################### FOR TIMEPOINT 2#########################################
# this converts the T1 tp2 to T1 baseline MNI, creates an output matrix file
def create_mat_T1tp2_T1MNI(in_file, bl_t1_mni):
        print ("Applying FLIRT to the following file for NON-BASELINE TIMEPOINT...")
        print (in_file)
        flt = fsl.FLIRT()
        flt.inputs.interp = "nearestneighbour"
        flt.inputs.dof = 6
        flt.inputs.in_file = in_file.replace("_T1mni", "") #t1 tp2
        flt.inputs.reference = bl_t1_mni
        flt.inputs.output_type = "NIFTI_GZ"
        flt.inputs.out_matrix_file = os.path.split(in_file)[0] + "/mni_affine.mat"
        flt.inputs.out_file = format_to_baseline_mni(in_file,"_T1mni.nii.gz")
        flt.cmdline
        flt.run()
        print(flt.cmdline)
        print ("FLIRT complete"); print()
        print (in_file, "FLIRT NON BASELINE complete");



# this applies the matrix created above to register tp2 flair, T2 and gad to T1 MNI
def apply_tp2_flirt(in_file,bl_t1_mni, affines):
    if not os.path.exists(in_file):
        print(in_file, "this file does not exist")
    else:
        for affine in affines:
            print ("Applying FLIRT to the following file...")
            print (in_file)
            flt = fsl.FLIRT()
            flt.inputs.apply_xfm = True
            flt.inputs.in_file = in_file
            flt.inputs.reference = bl_t1_mni #format_to_baseline_mni(t1_file,"_T1mni.nii.gz")
            flt.inputs.output_type = "NIFTI_GZ"
            flt.inputs.in_matrix_file = os.path.split(in_file)[0] + "/mni_affine.mat"
            flt.inputs.out_file = format_to_baseline_mni(in_file,"_T1mni.nii.gz")
            flt.cmdline
            flt.run()
            print(flt.cmdline)
            print ("FLIRT complete"); print()
            print (in_file, "FLIRT complete"); print

def apply_tp2_flirt_nochop(in_file,bl_t1_mni, affines):
    if not os.path.exists(in_file):
        print(in_file, "this file does not exist")
    else:
        print ("Applying FLIRT to the following file...")

        cmd = ["fslreorient2std", in_file, in_file.replace(".nii.gz", "_re2std.nii.gz")]
        proc = Popen(cmd, stdout=PIPE)
        output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]

        flt = fsl.FLIRT()
        flt.inputs.apply_xfm = True
        flt.inputs.in_file = in_file.replace(".nii.gz", "_re2std.nii.gz")
        flt.inputs.reference = bl_t1_mni #format_to_baseline_mni(t1_file,"_T1mni.nii.gz")
        flt.inputs.output_type = "NIFTI_GZ"
        matrix = in_file.replace("nii", "alignment")
        flt.inputs.in_matrix_file = os.path.split(matrix)[0] + "/mni_affine.mat"
        flt.inputs.out_file = format_to_baseline_mni(in_file,"_T1mni_nochop.nii.gz")
        flt.cmdline
        flt.run()
        print(flt.cmdline)
        print ("FLIRT complete"); print()
        print (in_file, "FLIRT complete"); print


def apply_lesion_flirt(lst_file, flair_file, t1_file, bl_t1_mni):
    lst = os.path.split(lst_file)[-1]
    if lst.startswith("no_FP"):
        flt = fsl.FLIRT()
        flt.inputs.interp = "nearestneighbour"
        flt.inputs.apply_xfm = True
        flt.inputs.in_file = lst_file
        flt.inputs.reference = bl_t1_mni #format_to_baseline_mni(t1_file,"_T1mni.nii.gz")
        flt.inputs.output_type = "NIFTI_GZ"
        flt.inputs.in_matrix_file = os.path.split(t1_file)[0] + "/mni_affine.mat"
        lesion_MNI = os.path.split(format_to_baseline_mni(flair_file,"_T1mni.nii.gz"))[0] + "/lesion_MNI.nii.gz"
        flt.inputs.out_file = lesion_MNI
        flt.cmdline
        flt.run()
        print(flt.cmdline)

        #new_in = os.path.split(t1_file)[-1]
        #ms = new_in.split("-")[0]
        #mse = new_in.split("-")[1]
        #msid = "ms" + ms.replace("ms", "").zfill(4)

        #mseid = "mse" + mse.replace("mse", "").zfill(4)


        msid = str(os.path.split(t1_file)[1].split('-')[0])
        mseid = str(os.path.split(t1_file)[1].split('-')[1])
        long = PBR_base_dir +'/'+ msid
        mni_long = PBR_base_dir +'/'+ msid + "/MNI/"


        if not os.path.exists(long):
            os.mkdir(long)
        if not os.path.exists(mni_long):
            os.mkdir(mni_long)
            print(mni_long)
        if not os.path.exists(mni_long+ "/lesion_"+mseid + ".nii.gz"):
            shutil.copyfile(lesion_MNI,mni_long + "/lesion_"+mseid + ".nii.gz")
            print(lesion_MNI,mni_long + "/lesion_"+mseid + ".nii.gz")

        flair_path = os.path.split(lesion_MNI)[0] +'/'+ os.path.split(format_to_baseline_mni(flair_file,"_T1mni.nii.gz"))[1]

        shutil.copyfile(flair_path, mni_long +'/'+ os.path.split(flair_path)[-1])
        print(flair_path, mni_long +'/'+ os.path.split(flair_path)[-1])

    else:
        print("no LST file to register")




def register_wm_mask(in_file, bl_t1_mni):
    new_in = os.path.split(in_file)[-1]
    ms = new_in.split("-")[0]
    mse = new_in.split("-")[1]
    msid = "ms" + ms.replace("ms", "").zfill(4)
    mse = "mse" + mse.replace("mse", "").zfill(4)
    gtech_path = "/data/pelletier1/genentech/sienax_yr89_lst_lesions/"#+ msid + "-" + mse
    for msid_mse in os.listdir(gtech_path):
        if msid_mse.startswith(msid + "-" + mse):
            print(msid_mse, gtech_path, "THIS PATH EXISTS")
            flt = fsl.FLIRT()
            flt.inputs.apply_xfm = True
            flt.inputs.in_file = gtech_path + "/"+ msid_mse + "/wm_mask.nii.gz"
            flt.inputs.reference = bl_t1_mni #format_to_baseline_mni(t1_file,"_T1mni.nii.gz")
            flt.inputs.output_type = "NIFTI_GZ"
            flt.inputs.in_matrix_file = os.path.split(in_file)[0] + "/mni_affine.mat"
            wm_MNI =  os.path.split(in_file)[0] + "/WM_MNI.nii.gz"
            flt.inputs.out_file = wm_MNI
            flt.cmdline
            flt.run()
            print(flt.cmdline)
            print (in_file, "FLIRT complete"); print

            cmd = ["fslmaths", wm_MNI, "-bin", wm_MNI]
            proc = Popen(cmd, stdout=PIPE)
            output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]

            cmd = ["fslmaths",gtech_path + "/"+ msid_mse + "/I_stdmaskbrain_pve_1.nii.gz", "-add", gtech_path + "/"+ msid_mse + "/I_brain_skull.nii.gz",gtech_path + "/"+ msid_mse + "/no_brain.nii.gz"  ]
            proc = Popen(cmd, stdout=PIPE)
            output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]

            flt = fsl.FLIRT()
            flt.inputs.interp = "nearestneighbour"
            flt.inputs.in_file = gtech_path + "/"+ msid_mse + "/no_brain.nii.gz"
            flt.inputs.reference = format_to_baseline_mni(in_file,"_T1mni.nii.gz")
            flt.inputs.in_matrix_file = os.path.split(in_file)[0] + "/mni_affine.mat"
            flt.inputs.output_type = "NIFTI_GZ"
            flt.inputs.apply_xfm = True
            gm_MNI = os.path.split(in_file)[0] + "/GM_MNI.nii.gz"
            flt.inputs.out_file = gm_MNI
            flt.cmdline
            flt.run()
            print(flt.cmdline)

            cmd = ["fslmaths", gm_MNI, "-bin", gm_MNI]
            proc = Popen(cmd, stdout=PIPE)
            output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]

            mni_long = PBR_base_dir +'/'+ str(ms) + "/MNI/"

            if os.path.exists(wm_MNI):
                print(wm_MNI)
            if not os.path.exists(mni_long):
                os.mkdir(mni_long)

            shutil.copyfile(gm_MNI,mni_long + "/gm_"+mseid + ".nii.gz")
            print(gm_MNI,mni_long + "/gm_"+mseid + ".nii.gz")

            shutil.copyfile(wm_MNI,mni_long + "/wm_"+mseid + ".nii.gz")
            print(wm_MNI,mni_long + "/wm_"+mseid + ".nii.gz")


def register_non_chop(in_file):
    if in_file.endswith(".nii.gz"):
        nifti = in_file.replace("alignment", "nii").replace("_T1mni", "")
        #chop = "/data/henry6/gina/nochop/chop.mat"
        chop2 = "/data/henry6/gina/nochop/chop2.mat"
        mni_paddy = "/data/henry6/gina/nochop/mnipaddy.nii.gz"

        reorient = Reorient2Std()
        reorient.inputs.in_file = nifti
        reorient.inputs.out_file = nifti.replace(".nii.gz", "_reorient.nii.gz")
        reorient.run()
        print(nifti, "Reorienting to std",nifti.replace(".nii.gz", "_reorient.nii.gz"))

        cmd = ["flirt", "-in", nifti.replace(".nii.gz", "_reorient.nii.gz"),"-ref", in_file.replace("_T1mni", ""), "-dof", "6","-interp", "nearestneighbour", "-omat", format_to_baseline_mni_nochop(in_file,"_chop.mat")]
        proc = Popen(cmd, stdout=PIPE)
        output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]

        cmd = ["convert_xfm", "-omat", format_to_baseline_mni_nochop(in_file,"_fullstd.mat"),"-concat", os.path.split(in_file)[0] + "/mni_affine.mat",format_to_baseline_mni_nochop(in_file,"_chop.mat")]
        proc = Popen(cmd, stdout=PIPE)
        output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]
        print(cmd)

        cmd = ["convert_xfm", "-omat", format_to_baseline_mni_nochop(in_file,"_fullstd.mat"),"-concat", chop2,format_to_baseline_mni_nochop(in_file,"_fullstd.mat") ]
        proc = Popen(cmd, stdout=PIPE)
        output = [l.decode("utf-8").split() for l in proc.stdout.readlines()[:]]

        flt = fsl.FLIRT()
        flt.inputs.apply_xfm = True
        flt.inputs.in_file = nifti.replace(".nii.gz", "_reorient.nii.gz")
        flt.inputs.reference = mni_paddy
        flt.inputs.output_type = "NIFTI_GZ"
        flt.inputs.in_matrix_file = format_to_baseline_mni_nochop(in_file,"_fullstd.mat")
        flt.inputs.out_file = format_to_baseline_mni_nochop(in_file,"_nochop.nii.gz")
        flt.cmdline
        flt.run()
        print(flt.cmdline, "FINISHED FLIRT REIGISTRATION")


def run_pbr_align(mseid):
    #from getpass import getpass
    alignment_folder = "/data/henry7/PBR/subjects/{0}/alignment".format(mseid)
    if os.path.exists(alignment_folder):
        cmd_rm = ['rm','-r', alignment_folder]
        print (cmd_rm)
        proc = Popen(cmd_rm)
        proc.wait()
        print("")

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
        #run_pbr_align(mseid)
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

def format_to_baseline_mni_nochop(in_file,extension,message="show"):
    out_path = in_file.split("alignment")[0] + "alignment/baseline_mni/no_chop"
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
    filepath = '/data/henry6/mindcontrol_ucsf_env/watchlists/long/VEO/EPIC_esha/{0}.txt'.format(msid)
    if os.path.exists(filepath):
        with open(filepath,'r') as f:
            timepoints = f.readlines()
            mse_bl = timepoints[0].replace("\n","")
            info = [msid, mse_bl, mseid]
            return info
    else:
        print ("no msid tracking txt file exists")
        return False

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

def remove_mat(affines):
    for affine in affines:
        mat = affine.replace(".txt", ".mat")
        os.remove(mat)

def conv_aff_mni(t1_mni_mat):
    cmd = ["c3d_affine_tool", "-itk", t1_mni_mat, "-o", t1_mni_mat.split(".")[0]+ ".mat"]
    proc = Popen(cmd, stdout=PIPE)
    global t1_mat
    t1_mat = t1_mni_mat.replace(".txt", ".mat")
    return t1_mat
    print(cmd)


def align_to_baseline(info):
    #1) check if TP1 has mni_angulated folder, even if TP1 = TPx

    check_mni_angulated_folder(info[1])

    #2) check if TP1 has /baseline_mni folder

    tp1_base_dir = '/data/henry7/PBR/subjects/{0}/alignment'.format(info[1])
    tp2_base_dir = '/data/henry7/PBR/subjects/{0}/alignment'.format(info[2])

    t1_mni_mat = tp1_base_dir+"/mni_angulated/affine.txt"
    conv_aff_mni(t1_mni_mat)

    tp1 = file_label(info[1],tp="BL")


    #3) check if TP1 = TPx
    if info[1] == info[2]:
        copy_mni_bl(tp1.bl_t1_mni)
        create_affine_tp1(tp1.t1_file, tp1.bl_t1_mni)
        register_non_chop(tp1.t1_file)
        register_non_chop(tp1.t2_file)
        register_non_chop(tp1.flair_file)
        register_non_chop(tp1.gad_file)

    else:
        print ('{0} will need additional alignment'.format(info[2]))
        tp2 = file_label(info[2])
        #conv_aff(tp2.affines)
        create_mat_T1tp2_T1MNI(tp2.t1_file, tp1.bl_t1_mni)
        #conv_xfm_tp2(tp2.affines,tp2.t1_file)
        apply_tp2_flirt(tp2.t2_file, tp1.bl_t1_mni, tp2.affines)
        apply_tp2_flirt(tp2.gad_file, tp1.bl_t1_mni, tp2.affines)
        apply_tp2_flirt(tp2.flair_file, tp1.bl_t1_mni,tp2.affines)
        apply_lesion_flirt(tp2.lst_file,tp2.flair_file, tp2.t1_file, tp1.bl_t1_mni)
        register_wm_mask(tp2.t1_file, tp1.bl_t1_mni)
        register_non_chop(tp2.t1_file)
        register_non_chop(tp2.t2_file)
        register_non_chop(tp2.flair_file)
        register_non_chop(tp2.gad_file)
        #remove_mat(tp2.affines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('ms', nargs="+")
    args = parser.parse_args()
    ms = args.ms
    #outdir = cc["output_directory"]
    print("msid is:", ms)

    for msid in ms:
        text_file = '/data/henry6/mindcontrol_ucsf_env/watchlists/long/VEO/EPIC_esha/{0}.txt'.format(msid)
        if os.path.exists(text_file):
            with open(text_file,'r') as f:
                timepoints = f.readlines()
                baseline_mse = timepoints[0].replace("\n","")
                check_for_trans_file(baseline_mse)
                for timepoint in timepoints:
                    mse_bl = timepoints[0].replace("\n","")
                    mseid = timepoint.replace("\n","")
                    print("Running...", timepoint)
                    info = [msid, mse_bl, mseid]
                    align_to_baseline(info)
                    print ("{}'s T1MNI registration complete".format(mseid))
            print ("{0}'s longitudinal registration complete".format(msid))
        else:
            print ("no msid tracking txt file exists")
            info = False
            continue

