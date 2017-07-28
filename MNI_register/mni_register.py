__author__ = 'sf522915'
from nipype.interfaces.base import (BaseInterface, TraitedSpec, traits, File, traits,
                                    OutputMultiPath, BaseInterfaceInputSpec, FileNotFoundError,
                                    isdefined, InputMultiPath)

from ...config import config
import os
from ...base import PBRBaseInterface, PBRBaseInputSpec, register_workflow


def chopper(in_file):
    import subprocess
    from nipype.utils.filemanip import split_filename
    import os


class MNIAngulationInputSpec(PBRBaseInputSpec):
    t1_files = InputMultiPath(File(exists=True))
    t2_files = InputMultiPath(File(exists=True))
    gad_files = InputMultiPath(File(exists=True))
    flair_files = InputMultiPath(File(exists=True))

class MNIAngulationOutputSpec(TraitedSpec):
    t1_files = traits.List(File(exists=True))
    flair_files = OutputMultiPath(File(exists=True))
    t2_files = OutputMultiPath(File(exists=True))
    gad_files = OutputMultiPath(File(exists=True))
    affines = traits.List(File(exists=True))
    t1_mask = traits.List(File(exists=True), minlen=1)




class MNIAngulation(PBRBaseInterface):
    input_spec = MNIAngulationInputSpec
    output_spec = MNIAngulationOutputSpec
    flag = "mni_align"
    output_folder = "mni_alignment"
    connections = [("nifti", "t1_files", "t1_files"),
                   ("nifti", "t2_files", "t2_files"),
                   ("nifti", "gad_files", "gad_files"),
                   ("nifti", "flair_files", "flair_files")]

    def _run_interface_pbr(self, runtime):
        import nipype.interfaces.io as nio
        import nipype.pipeline.engine as pe
        import nipype.interfaces.fsl as fsl
        import nipype.interfaces.ants as ants
        import nipype.interfaces.utility as niu
        from nipype.interfaces.c3 import C3dAffineTool
        import nipype.interfaces.fsl as fsl

        wf = pe.Workflow(name="MNIAng_%s"%self.inputs.mseID)
        wf.base_dir = config["working_directory"]

        chop = pe.MapNode(niu.Function(input_names=["in_file"],
                                output_names=["out_file"],
                                function=chopper),
                   name="chopper", iterfield=["in_file"])

        flirt2temp = pe.Node(fsl.FLIRT(dof=6),#, out_matrix_file=True),
                             name="flirt2mni")
        flirt2temp.inputs.reference = config["mni_template"]
        #flirt2temp.inputs.in_file = self.inputs.t1_files[-1] #the last t1_file in case the first sucks

        pickfirst = lambda x: x[0]

        bet = pe.Node(fsl.BET(robust=True, mask=True), name="skull_strip_t1")


        wf.connect(chop, ("out_file", pickfirst), bet, "in_file")
        wf.connect(bet, "out_file", flirt2temp, "in_file")


        #flirtwithin.inputs.reference = self.inputs.t1_files[-1]

        sinker = pe.Node(nio.DataSink(), name="sinker")
        sinker.inputs.base_directory = config["output_directory"]

        sink2 = sinker.clone("sinker2")
        sink2.inputs.base_directory = config["output_directory"]

        sink2.inputs.container = self.inputs.mseID
        sink2.inputs.substitutions = [("_ROI_reoriented",""),("_chopper0", "")]

        list_of_nii = []
        #if len(self.inputs.t1_files) > 1:
        #    list_of_nii.append(self.inputs.t1_files[:-1]) #all but the last

        remaining_files = [self.inputs.t1_files, self.inputs.t2_files, self.inputs.flair_files, self.inputs.gad_files]

        for attrib in remaining_files:
            if len(attrib):
                list_of_nii += attrib


        if len(list_of_nii) == 0:
            raise ValueError("***No T1, T2, FLAIR or Gad file in the nifti list, please check your mse status file***")

        chop.inputs.in_file = list_of_nii

        if len(list_of_nii) == 1:
            #There is only 1 file, so just chop and copy it over
            print("WARNING: ONLY 1 FILE")
            wf.connect(chop, ("out_file", pickfirst), sink2, "alignment.@choppedt1")
            wf.connect(bet, "mask_file", sink2, "alignment.@mask_file")
            wf.config = {"execution": {"crashdump_dir": os.path.join(config["crash_directory"],
                                                                 self.inputs.mseID,
                                                                 self.flag)}}
            wf.run()
            return runtime


        flirtwithin = pe.MapNode(fsl.FLIRT(dof=6,
                                           cost="nearestneighbour"),
                                           out_matrix_file=True),
                              name="flirtwithin", iterfield=["in_file"])
        wf.connect(chop, ("out_file", pickfirst), flirtwithin, "reference")
        #Take t1 file as reference

        picknotfirst = lambda x: x[1:]  #way of chosing the last scan of a given sequence
        #flirtwithin.inputs.in_file = list_of_nii
        wf.connect(chop, ("out_file", picknotfirst), flirtwithin, "in_file")

        convert2itk = pe.MapNode(C3dAffineTool(), name='convert2itk', iterfield=["transform_file", "source_file"])
        convert2itk.inputs.fsl2ras = True
        convert2itk.inputs.itk_transform = True
        #convert2itk.inputs.reference_file = self.inputs.t1_files[-1]
        wf.connect(chop, ("out_file", pickfirst), convert2itk, "reference_file")
        wf.connect(flirtwithin, "out_matrix_file", convert2itk, "transform_file")
        #convert2itk.inputs.source_file = list_of_nii
        wf.connect(chop, ("out_file", picknotfirst), convert2itk, "source_file")

        convert2itk2 = pe.Node(C3dAffineTool(), name='convert2itk2')
        convert2itk2.inputs.fsl2ras = True
        convert2itk2.inputs.itk_transform = True
        wf.connect(flirt2temp, "out_matrix_file",convert2itk2, "transform_file")
        convert2itk2.inputs.reference_file = config["mni_template"]
        #convert2itk2.inputs.source_file = self.inputs.t1_files[-1]
        wf.connect(chop, ("out_file", pickfirst), convert2itk2, "source_file")

        applyxfms = pe.MapNode(ants.ApplyTransforms(dimension=3),
                               name="applycombinedxfm",
                               iterfield=["input_image", "transforms"])
        applyxfms.inputs.reference_image = config["mni_template"]
        #applyxfms.inputs.input_image = list_of_nii
        wf.connect(chop, "out_file", applyxfms, "input_image")

        def combine_xfms(to_mni, others_list):
            out = [[to_mni]]
            for o in others_list:
                out.append([to_mni, o])
            return out

        stupid = pe.Node(niu.Function(input_names=["to_mni", "others_list"],
                                      output_names=["out"],
                                      function=combine_xfms),
                         name="combiner")

        wf.connect(convert2itk2, "itk_transform", stupid, "to_mni")
        wf.connect(convert2itk, "itk_transform", stupid, "others_list")
        wf.connect(stupid, "out", applyxfms, "transforms")





        wf.connect(applyxfms, "output_image", sinker, "alignment.mni_angulated.@otherfiles")
        wf.connect(flirt2temp, "out_file", sink2, "alignment.mni_angulated.@t1ref")
        wf.connect(flirtwithin, "out_file", sinker, "alignment.@within")
        wf.connect(chop, ("out_file", pickfirst), sink2, "alignment.@choppedt1")
        wf.connect(bet, "mask_file", sink2, "alignment.@mask_file")

        def subs(other_files):
            sd = [t.split("/")[-1].split(".nii.gz")[0] for t in other_files]
            N = len(sd)
            subs =  [("_applycombinedxfm%d"%(i), "") for i in range(50)[::-1]]
            subs += [("_convert2itk%d/"%(N-i-1), "{}_".format(sd[N-i-1])) for i, name in enumerate(sd)]
            subs.append(("_chop_trans",""))
            subs.append(("_chop_affine", "_affine"))
            subs.append(("_chop_flirt", ""))
            subs.append(("_chopper0/", ""))
            subs.append(("_ROI_reoriented_flirt", ""))
            subs.append(("_ROI_reoriented", ""))
            subs += [("_flirtwithin%d/"%i, "") for i in range(20)[::-1]]
            subs.append(("_chop.", "."))
            return subs

        subsnode = pe.Node(niu.Function(input_names=["other_files"],
                                        output_names=["subs"],
                                        function=subs),
                           name="subs")

        wf.connect(convert2itk2, "itk_transform", sinker, "alignment.mni_angulated.@to_mni")
        wf.connect(convert2itk, "itk_transform", sinker, "alignment.@to_t1")

        #sinker.inputs.substitutions = subs()
        wf.connect(chop, ("out_file", picknotfirst), subsnode, "other_files")
        wf.connect(subsnode, "subs", sinker, "substitutions")
        sinker.inputs.container = self.inputs.mseID

        wf.write_graph(graph2use = 'orig')
        wf.config["Execution"] = {"keep_inputs": True, "remove_unnecessary_outputs": False}
        wf.config = {"execution": {"crashdump_dir": os.path.join(config["crash_directory"],
                                                                 self.inputs.mseID,
                                                                 self.flag)}}
        try:
            wf.run()
        except RuntimeError:
            print("\n\n============================= \n\n THERE MAY HAVE BEEN AN ERROR, BUT MAYBE THERE WAS ONLY 1 FILE \n\n ==================================\n\n")

        return runtime

    def _get_output_folder(self):
        return "alignment"


    def _list_outputs(self):
        #print self.inputs
        from glob import glob
        from pbr.workflows.nifti_conversion.utils import filter_files, filter_local_heuristic
        import pbr
        from nipype.utils.filemanip import load_json
        heuristic_file = os.path.join(os.path.split(pbr.__file__)[0], "heuristic.json")
        heuristic = load_json(heuristic_file)["filetype_mapper"]
        local_heuristic = os.path.join(config["output_directory"],
                                       self.inputs.mseID, "nii", "heuristic.json")
        filter_files_func = filter_files
        if os.path.exists(local_heuristic):
            heuristic = load_json(local_heuristic)
            filter_files_func = filter_local_heuristic
            print("USING SUBJECT HEURISTIC")

        outputs = self._outputs().get()

        remaining_files = [self.inputs.t1_files,
                           self.inputs.t2_files,
                           self.inputs.flair_files,
                           self.inputs.gad_files]

        list_of_nii= []

        for attrib in remaining_files:
            if len(attrib):
                list_of_nii += attrib

        names = [q.split("/")[-1].split(".nii.gz")[0] for q in list_of_nii]
        out = os.path.join(config["output_directory"],self.inputs.mseID,"alignment")

        all_niftis = glob(os.path.join(out,"*.nii.gz"))
        if len(all_niftis) < len(names):
            raise FileNotFoundError

        outputs["t1_files"] = filter_files_func(all_niftis, "T1", heuristic)
        outputs["t2_files"] = filter_files_func(all_niftis, "T2", heuristic)
        outputs["flair_files"] = filter_files_func(all_niftis, "FLAIR", heuristic)
        outputs["gad_files"] =filter_files_func(all_niftis, "T1_Gad", heuristic)


        outputs["affines"] = glob(os.path.join(out, "*.txt"))
        outputs["t1_mask"] = glob(os.path.join(out,"*_brain_mask.nii.gz"))

        return outputs

register_workflow(MNIAngulation)