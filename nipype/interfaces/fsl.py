"""The fsl module provides basic functions for interfacing with fsl tools.

Currently these tools are supported:

  * BET: brain extraction
  * FAST: segmentation and bias correction
  * FLIRT: linear registration
  * FNIRT: non-linear warp

Examples
--------
See the docstrings for the individual classes (Bet, Fast, etc...) for
'working' examples.

"""

import os
import subprocess
from copy import deepcopy
from glob import glob

import enthought.traits.api as traits
import enthought.traits.ui.api as tui

from nipype.utils.filemanip import fname_presuffix
from nipype.interfaces.base import (Bunch, CommandLine, 
                                    load_template, InterfaceResult)
from nipype.utils import setattr_on_read

import warnings
warn = warnings.warn

warnings.filterwarnings('always', category=UserWarning)
# If we don't like the way python is desplaying things, we can override this,
# e.g.:
# def warnings.showwarning(message, category, filename, lineno, file=None,
# line=None):
#     print message

def fslversion():
    """Check for fsl version on system

    Parameters
    ----------
    None

    Returns
    -------
    version : string
       version number as string 
       or None if FSL not found

    """
    # find which fsl being used....and get version from
    # /path/to/fsl/etc/fslversion
    clout = CommandLine('which fsl').run()

    if clout.runtime.returncode is not 0:
        # fsl not found
        return None
    out = clout.runtime.stdout
    basedir = os.path.split(os.path.split(out)[0])[0]
    clout = CommandLine('cat %s/etc/fslversion'%(basedir)).run()
    out = clout.runtime.stdout
    return out.strip('\n')


def fsloutputtype(ftype=None):
    """Check and or set the global FSL output file type FSLOUTPUTTYPE
    
    Parameters
    ----------
    ftype :  string
        Represents the file type to set
        based on string of valid FSL file types
        ftype == None to get current setting/ options

    Returns
    -------
    fsl_ftype : string
        Represents the current environment setting of FSLOUTPUTTYPE
    ext : string
        The extension associated with the FSLOUTPUTTYPE

    """
    ftypes = {'NIFTI':'nii',
              'ANALYZE':'hdr',
              'NIFTI_PAIR':'hdr',
              'ANALYZE_GZ':'hdr.gz',
              'NIFTI_GZ':'nii.gz',
              'NIFTI_PAIR_GZ':'hdr.gz',
              None: 'env variable FSLOUTPUTTYPE not set'}

    if ftype is None:
        # get environment setting
        fsl_ftype = os.getenv('FSLOUTPUTTYPE')
        for key in ftypes.keys():
            print '%s = \"%s\"'%(key, ftypes[key])

    else:
        # set environment setting
        fsl_ftype = ftype
        os.environ['FSLOUTPUTTYPE'] = fsl_ftype
    
    print 'FSLOUTPUTTYPE = %s (\"%s\")'%(fsl_ftype, ftypes[fsl_ftype])
    return fsl_ftype,ftypes[fsl_ftype]
        

class FSLCommand(CommandLine):
    '''General support for FSL commands'''
    # Would be nice to use:
    # @traits.chached_property(depends_on='inputs.*')
    @property
    def cmdline(self):
        """validates fsl options and generates command line argument"""
        allargs = [self.cmd]
        allargs.extend(self._parse_inputs())
        return ' '.join(allargs)

    def run(self):
        """Execute the command.
        
        Returns
        -------
        result : InterfaceResult
            A `Bunch` object with a copy of self in `interface`

        """
        results = self._runner()
        if result.runtime.returncode == 0:
            result.outputs = self.aggregate_outputs()

        return result

    def _parse_inputs(self, skip=()):
        """validate options in the opt_map. If set to None ignore.
        """
        allargs = []

        if self.inputs.args != self.inputs.trait('args').default:
            allargs.extend(value)

        # I'd like to just iterate through non-default traits
        flags = self.inputs.class_traits(flag=lambda x: x is not None)
        for opt, value in flags.items():
            try:
                argstr = self.opt_map[opt]
                # Change this stuff to check type of the trait
                if argstr.find('%') == -1:
                    if value is True:
                        allargs.append(argstr)
                    elif value is not False:
                        raise TypeError('Boolean option %s set to %s' % 
                                         (opt, str(value)) )
                else:
                    allargs.append(argstr % getattr(self, opt))
            except TypeError, err:
                # Perhaps these should be proper warnings?
                warn('For option %s in Fast, %s' % (opt, err.message))
            except KeyError:                   
                warn('option %s not supported' % (opt))
        
        return allargs

    def inputs_help(self):
        '''Generate help from our traits desc strings'''
        template = "%s : %s\n    %s"
        all_help = [template % (name, t.trait_type.info_text, t.get_help()) 
                            for name, t in self.inputs.traits().items()]
        print '\n'.join(all_help)
        

class Bet(FSLCommand):
    """use fsl bet for skull stripping

    Options
    -------

    To see optianl arguments
    Bet().inputs_help()


    Examples
    --------
    >>> fsl.Bet().inputs_help()
    >>> better = fsl.Bet(frac=0.5)
    >>> betted = better.run('infile', 'outfile')
    >>> better2 = better.update(frac=0.3)

    >>> btr = fsl.Bet(infile='infile', outfile='outfile', frac=0.5)
    >>> btd = btr.run()
    """

    @property
    def cmd(self):
        """sets base command, not editable"""
        return 'bet'

    def inputs_help(self):
        """
        Mandatory Parameters
        --------------------
        (all default to None and are unset)
        
        infile : /path/to/file
            file to skull strip 

        Optional Parameters
        -------------------
        (all default to None and are unset)
        
        outfile : /path/to/outfile
            path/name of skullstripped file
        outline : Bool
            generate brain surface outline overlaid onto original image
        mask : Bool
            generate binary brain mask
        skull : Bool	
            generate approximate skull image
        nooutput : Bool	
            don't generate segmented brain image output
        frac : float
            fractional intensity threshold (0->1); fsldefault=0.5; 
            smaller values give larger brain outline estimates
        vertical_gradient : float		
            vertical gradient in fractional intensity threshold (-1->1); fsldefault=0
            positive values give larger brain outline at bottom, smaller at top
        radius : float	
            head radius (mm not voxels); initial surface sphere is set to half of this
        center : list of ints [x,y,z]
            centre-of-gravity (voxels not mm) of initial mesh surface.
        threshold : Bool	
            apply thresholding to segmented brain image and mask
        mesh : Bool	
            generates brain surface as mesh in vtk format
        verbose : Bool	
            switch on diagnostic messages
	
        flags = unsupported flags, use at your own risk  ['-R']

        """
        print self.inputs_help.__doc__

    def _populate_inputs(self):
        self.inputs = Bunch(infile=None,
                          outfile=None,
                          outline=None,
                          mask=None,
                          skull=None,
                          nooutput=None,
                          frac=None,
                          vertical_gradient=None,
                          radius=None,
                          center=None,
                          threshold=None,
                          mesh=None,
                          verbose=None, 
                          flags=None)

    def _parse_inputs(self):
        """validate fsl bet options
        if set to None ignore
        """
        out_inputs = []
        inputs = {}
        [inputs.update({k:v}) for k, v in self.inputs.iteritems() if v is not None ]
        for opt in inputs:
            if opt is 'infile':
                continue
            if opt is 'outfile':
                continue
            if opt is 'frac':
                val = float(inputs['frac'])
                out_inputs.extend(['-f','%.2f'%(val)])
                continue
            if opt is 'center':
                val = [float(x) for x in inputs['center']]
                if len(val) is not 3:
                    raise ValueError('three values required for center option')
                out_inputs.extend(['-c' , '%s %s %s'%(val[0],val[1],val[2])])
                continue
            if opt is 'vertical_gradient':
                val = float(inputs['vertical_gradient'])
                out_inputs.extend(['-g','%.2f'%(val)])
                continue
            if opt is 'outline':
                if inputs[opt]:
                    out_inputs.extend(['--outline'])
                continue
            if opt is 'mask':
                if inputs[opt]:
                    out_inputs.extend(['--mask'])
                continue
            if opt is 'skull':
                if inputs[opt]:
                    out_inputs.extend(['--skull'])
                continue
            if opt is 'nooutput':
                if inputs[opt]:
                    out_inputs.extend(['--nooutput'])
                continue
            if opt is 'radius':
                val = float(inputs[opt])
                out_inputs.extend(['--radius %f'%(val)])
            if opt is 'threshold':
                if inputs[opt]:
                    out_inputs.extend(['--threshold'])
                continue
            if opt is 'mesh':
                if inputs[opt]:
                    out_inputs.extend(['--mesh'])
                continue
            if opt is 'verbose':
                if inputs[opt]:
                    out_inputs.extend(['--verbose'])
                continue
            if opt is 'flags':
                out_inputs.extend(inputs[opt])
                continue
            print 'option %s not supported'%(opt)

        if self.inputs['infile']:
            out_inputs.insert(0, str(self.inputs['infile']))
        if self.inputs['outfile']:
            out_inputs.insert(1, str(self.inputs['outfile']))
        else:
            pth,fname = os.path.split(self.inputs['infile'])
            out_inputs.insert(1, '%s' % os.path.join(self.inputs.get('cwd',pth),
                                                     fname_presuffix(fname,suffix='_bet')))
                              
        return out_inputs


    def run(self, infile=None, outfile=None, **inputs):
        """Execute the command.

        Parameters
        ----------
        infile : filename
            file to be skull stripped, can be passed as input
        outfile : filename
            file handle to save output, if None, <filename_bet> 
            will be used

        Returns
        -------
        results : Bunch
            A `Bunch` object with a copy of self in `interface`
            runtime : Bunch containing stdout, stderr, returncode, commandline
            
        """
        self.inputs.update(**inputs)

        if not infile and not self.inputs.infile:
                raise AttributeError('bet requires an input file')
        if infile:
            self.inputs.infile = infile
        if outfile:
            self.inputs.outfile = outfile
        
        results = self._runner()
        if results.runtime.returncode == 0:
            results.outputs = self.aggregate_outputs()

        return results        


    def outputs_help(self):
        """
        Optional Parameters
        -------------------
        (all default to None and are unset)
        
        outfile : /path/to/outfile
            path/name of skullstripped file
        maskfile : Bool
            binary brain mask if generated
        """
        print self.outputs_help.__doc__

    def aggregate_outputs(self):
        outputs = Bunch(outfile = None,
                        maskfile = None)
        if self.inputs.outfile:
            outfile = self.inputs.outfile
        else:
            pth,fname = os.path.split(self.inputs['infile'])
            outfile = os.path.join(self.inputs.get('cwd',pth),
                                   fname_presuffix(fname,suffix='_bet'))
        assert len(glob(outfile))==1, "Incorrect number or no output files %s generated"%outfile
        outputs.outfile = outfile
        maskfile = fname_presuffix(outfile,suffix='_mask')
        outputs.maskfile = glob(maskfile)
        if len(outputs.maskfile) > 0:
            outputs.maskfile = outputs.maskfile[0]
        else:
            outputs.maskfile = None
        return outputs

# Consider using compound traits made with Either:
# ArrayOrNone = Either(Array, None)

# More notes:
# _anytrait_changed -> keep set of traits that changed
# What are enter_set and auto_set (for Traits.Range)?

class FastInputs(traits.HasTraits):
    '''Inputs for Fast'''
    # '*' is no good here :(
    # view = tui.View(
    #            # tui.Group(
    #            # tui.Group(
    #                tui.Label('Required Inputs'),
    #                tui.Item('inputs', editor=tui.ListStrEditor(auto_add=True)), 
    #            #     show_labels=False,
    #            #     label='inputs',
    #            #     show_border=True, 
    #            #     scrollable=True
    #            # ),
    #            #),
    #            'number_classes', 'bias_iters', 'bias_lowpass',
    #            resizable=True,
    #            #height=0.5,
    #            title='Inputs for FAST',
    #        )

    infiles = traits.List(traits.File, 
                         editor=tui.ListEditor(rows=3, style='custom',
                         ui_kind='subpanel'), #auto_add=True),
        desc="files to run on ['/path/to/afile', /path/to/anotherfile']")
    number_classes = traits.Int(flag='--class %d ',
        desc='number of tissue-type classes, (default=3)')
    bias_iters = traits.Int(flag='--iter %d',
        desc='number of main-loop iterations during bias-field removal' \
        '(default=4)')
    bias_lowpass = traits.Int(flag='--lowpass %d',
        desc='bias field smoothing extent (FWHM) in mm (default=20)')
    img_type = traits.Int(flag='--type %d',
        desc='type of image 1=T1, 2=T2, 3=PD; (default=T1)')
    init_seg_smooth = traits.Float(flag='--fHard %f',
        desc='initial segmentation spatial smoothness (during bias field' \
        'estimation); default=0.02')
    segments = traits.Bool(flag='--segments',
        desc='outputs a separate binary image for each tissue type')
    init_transform = traits.Str(flag='-a %s', # a valid filename
        desc='initialise using priors; you must supply a FLIRT transform' \
        '<standard2input.mat>')
    # This option is not really documented on the Fast web page:
    # http://www.fmrib.ox.ac.uk/fsl/fast4/index.html#fastcomm
    # I'm not sure if there are supposed to be exactly 3 args or what
    # May want to use a Tuple or a List Trait depending on how this is supposed
    # to be
    other_priors = traits.Tuple('', '', '',  # should be fnames
        flag='-A %s %s %s',
        desc="<prior1> <prior2> <prior3>    alternative prior images")
    nopve = traits.Bool(flag='--nopve',
        desc='turn off PVE (partial volume estimation)')
    output_biasfield = traits.Bool(flag='-b',
        desc='output estimated bias field')
    output_biascorrected = traits.Bool(flag='-B',
        desc='output bias-corrected image')
    nobias = traits.Bool(flag='--nobias',
        desc='do not remove bias field')
    n_inputimages = traits.Int(flag='--channels %d',
        desc='number of input images (channels); (default 1)')
    out_basename = traits.Str(flag='--out %s', # should be a filename
        desc='output basename for output images')
    use_priors = traits.Bool(flag='--Prior',
        desc='use priors throughout; you must also set the init_transform' \
        'option')
    segment_iters = traits.Int(flag='--init %d',
        desc='number of segmentation-initialisation iterations; (default=15)')
    mixel_smooth = traits.Float(flag='--mixel %f',
        desc='spatial smoothness for mixeltype; (default=0.3)')
    iters_afterbias = traits.Int(flag='--fixed %d',
        desc='number of main-loop iterations after bias-field removal;' \
        '(default=4)')
    hyper = traits.Float(flag='--Hyper %f',
        desc='segmentation spatial smoothness; (default=0.1)')
    verbose = traits.Bool(flag='--verbose',
        desc='switch on diagnostic messages')
    manualseg = traits.Str(flag='--manualseg %s', # a filename
        desc='Filename containing intensities')
    probability_maps = traits.Bool(flag='-p',
        desc='outputs individual probability maps')
    args = traits.ListStr(
        desc="unsupported flags, use at your own risk  ['-R']")

    # hack for now - Traits does our "update" with "set"
    def update(self, *args, **kwargs):
        self.set(*args, **kwargs)

class Fast(FSLCommand):
    """use fsl fast for segmenting, bias correction

    Options
    -------
    see  
    fsl.Fast().inputs_help()
    
    Example
    -------
    >>> faster = fsl.Fast(out_basename = 'myfasted')
    >>> fasted = faster.run(['file1','file2'])
    >>> fsl.Fast().inputs_help()

    >>> faster = fsl.Fast(infiles=['filea','fileb'], 
                          out_basename = 'myfasted')
    >>> fasted = faster.run()
    """

    @property
    def cmd(self):
        """sets base command, not editable"""
        return 'fast'


    # TODO: Can handle the class-specific requirements with traits and hoist
    # this method to FSLCommand
    def run(self, infiles=None, **inputs):
        """Execute the FSL fast command.

        Parameters
        ----------
        infiles : filename(s)
            file(s) to be segmented or bias corrected
        
        Returns
        -------
        result : InterfaceResults
            A `Bunch` object with a copy of self in `interface`
            runtime : Bunch containing stdout, stderr, returncode, commandline
            
        """
        self.inputs.update(inputs)

        if not infiles and not self.inputs.infiles:
                raise AttributeError('fast requires input file(s)')
        if infiles:
            if type(infiles) is not list:
                infiles = [infiles]
            self.inputs.infiles = infiles
        
        
        results = self._runner()
        if results.runtime.returncode == 0:
            results.outputs = self.aggregate_outputs()

        return results        

    def _parse_inputs(self):
        '''Call our super-method, then add our input files'''
        # Could do other checking above and beyond regular _parse_inputs here
        allargs = super(Fast, self)._parse_inputs()
        allargs.extend(self.inputs.infiles)

        return allargs



class Flirt(FSLCommand):
    """use fsl flirt for coregistration
    
    Options
    -------
    fsl.Flirt().inputs_help()
    
    Examples
    --------
    
    >>> flirtter = fsl.Flirt(bins=640, searchcost='mutualinfo')
    >>> flirtted = flirtter.run(infile='involume.nii', 
    reference='reference.nii',
    outfile='moved.nii', 
    outmatrix='in_to_ref.mat')
    >>> flirtted_est = flirtter.run(infile='involume.nii', 
    reference='reference.nii',
    outfile=None
    outmatrix='in_to_ref.mat')
    >>> xfm_apply = flirtter.applyxfm(infile='involume.nii', 
    reference='reference.nii',
    inmatrix='in_to_ref.mat',
    outfile='moved.nii')
    
    >>> fls.Flirt().inputs_help()
    
    
    >>> flirter = fsl.Flirt(infile='subject.nii',
    reference='template.nii',
    outfile='moved_subject.nii',
    outmatrix='subject_to_template.mat')
    >>> flitrd = flirter.run()
    
    
    """
        
    @property
    def cmd(self):
        """sets base command, not editable"""
        return "flirt"

    opt_map = {'datatype':           '-datatype %d ',
               'cost':               '-cost %s',
               'searchcost':         '-searchcost %s',
               'usesqform':          '-usesqform',
               'displayinit':        '-displayinit',
               'anglerep':           '-anglerep %s',
               'interp':             '-interp',
               'sincwidth':          '-sincwidth %d',
               'sincwindow':         '-sincwindow %s',
               'bins':               '-bins %d',
               'dof':                '-dof %d',
               'noresample':         '-noresample',
               'forcescaling':       '-forcescaling',
               'minsampling':        '-minsamplig %f',
               'paddingsize':        '-paddingsize %d',
               'searchrx':           '-searchrx %d %d',
               'searchry':           '-searchry %d %d',
               'searchrz':           '-searchrz %d %d',
               'nosearch':           '-nosearch',
               'coarsesearch':       '-coarsesearch %d',
               'finesearch':         '-finesearch %d',
               'refweight':          '-refweight %s',
               'inweight':           '-inweight %s',
               'noclamp':            '-noclamp',
               'noresampblur':       '-noresampblur',
               'rigid2D':            '-2D',
               'verbose':            '-v %d',
               'flags':              '%s'}


    #@property
    #def cmdline(self):
    #    """validates fsl options and generates command line argument"""
    #    valid_inputs = self._parse_inputs()
    #    allargs = self.args + valid_inputs
    #    return ' '.join(allargs)
  
        
    def inputs_help(self):
        doc = """

        POSSIBLE OPTIONS
        -----------------
        (all default to None and are unset)
        infile : /path/to/file
            file to be moved/registered into space of
            reference image
        outfile : /path/to/newfilename
            file to save the moved/registered image
        reference : /path/to/reference_image
            file of reference image
        outmatrix : /path/to/matrixfile.mat
            file that holds transform mapping infile to reference
        datatype : string {'char','short','int','float','double'}
            (force output data type)
        cost : string {'mutualinfo','corratio','normcorr','normmi','leastsq','labeldiff'}  
            (fsldefault is corratio)
        searchcost : string 
            {'mutualinfo','corratio','normcorr','normmi','leastsq','labeldiff'}  
            (FSL default = 'corratio')
        usesqform : Bool
            (initialise using appropriate sform or qform)
        displayinit : Bool
            (display initial matrix)
        anglerep :string {'quaternion','euler'}       
            (fsldefault is euler)
        interp : string  {'trilinear','nearestneighbour','sinc'}  
            (final interpolation: fsldefault = trilinear)
        sincwidth : int
            full-width in voxels  (fsldefault is 7)
        sincwindow : string {'rectangular','hanning','blackman'}
            function on the data in the sinc window
        bins : int 
            number of histogram bins   (fsldefault is 256)
        dof : int
            number of transform dofs (degrees of freedom)(fsldefault is 12)
        noresample : Bool                        
            (do not change input sampling)
        forcescaling : Bool                      
            (force rescaling even for low-res images)
        minsampling : float
            vox_dim (set minimum voxel dimension for sampling (in mm))
        applyisoxfm : float <scale>               
            used with applyxfm only! but forces isotropic resampling)
        paddingsize : int 
            number of voxels (for applyxfm: interpolates outside image by size)
        searchrx : list of ints [-90,90]
            [<min_angle> <max_angle>]  (angles in degrees: fsldefault is -90 90)
        searchry : list of ints [-90, 90]
            [<min_angle> <max_angle>]  (angles in degrees: default is -90 90)
        searchrz : list of ints [-90,90]
            [<min_angle> <max_angle>]  (angles in degrees: default is -90 90)
        nosearch : Bool
            (sets all angular search ranges to 0 0)
        coarsesearch : int <delta_angle>        
            (angle in degrees: fsldefault is 60)
        finesearch : int <delta_angle>          
            (angle in degrees: default is 18)
        refweight : string  <volume filename>                
            (use weights for reference volume)
        inweight : string <volume filename>                 
            (use weights for input volume)
        noclamp : Bool
            (do not use intensity clamping)
        noresampblur : Bool
            (do not use blurring on downsampling)
        rigid2D : Bool
            (use 2D rigid body mode - ignores dof)
        verbose : int <num>
            controls amount of output (0 is least and is fsldefault)
        
        flags : list 
            unsupported flags, use at your own risk!!  
            flags = ['-i']

        """
        print doc
    def _populate_inputs(self):
        self.inputs = Bunch(infile=None,
                            outfile=None,
                            reference=None,
                            outmatrix=None,
                            inmatrix=None,
                            datatype=None,
                            cost=None,
                            searchcost=None,
                            usesqform=None,
                            displayinit=None,
                            anglerep=None,
                            interp=None,
                            sincwidth=None,
                            sincwindow=None,
                            bins=None,
                            dof=None,
                            noresample=None,
                            forcescaling=None,
                            minsampling=None,
                            applyisoxfm=None,
                            paddingsize=None,
                            searchrx=None,
                            searchry=None,
                            searchrz=None,
                            nosearch=None,
                            coarsesearch=None,
                            finesearch=None,
                            refweight=None,
                            inweight=None,
                            noclamp=None,
                            noresampblur=None,
                            rigid2D=None,
                            verbose=None,
                            flags=None)
    def _parse_inputs(self):
        '''Call our super-method, then add our input files'''
        # Could do other checking above and beyond regular _parse_inputs here
        allargs = super(Flirt, self)._parse_inputs(skip=('infile','outfile',
                                                         'reference', 'outmatrix',
                                                         'inmatrix'))
        possibleinputs = [(self.inputs.outfile,'-out'),
                          (self.inputs.inmatrix, '-init'),
                          (self.inputs.outmatrix, '-omat'),
                          (self.inputs.reference, '-ref'),
                          (self.inputs.infile, '-in')]
        
        for val, flag in possibleinputs:
            if val:
                allargs.insert(0,'%s %s'%(flag, val))
        
        return allargs

    

    def run(self, infile=None, reference=None, outfile=None, outmatrix=None):
        """ runs flirt command
         

        Parameters
        ----------
        infile : filename
            filename of volume to be moved
        reference : filename
            filename of volume used as target for registration
        outfile : filename
            filename of new volume of infile moved to space of reference
            if None,  only the transformation matrix will be calculated
        outmatrix : filename  q
            filename holding transformation matrix in asci format
            if None, the output matrix will not be saved to a file

        Returns
        --------
        flirt : object
            return new flirt object with updated fields

        Examples
        --------
        flirted = Flirt().run(infile, reference, outfile)
        flirted_estimate = Flirt().run(infile, reference, outfile=None, outmatrix=outmatrix)
        flirt_apply = Flirt().applyxfm(infile, reference, inmatrix, outfile)
            
        
        """
        #newflirt = self.update()
        if infile is None:
            if self.inputs.infile is None:
                raise ValueError('infile is not specified')
            else:
                infile = self.inputs.infile
        if reference is None:
            if self.inputs.reference is None:
                raise ValueError('reference is not specified')
            else:
                reference = self.inputs.reference
        if outfile is None:
            outfile = self.inputs.outfile
        if outmatrix is None:
            outmatrix = self.inputs.outmatrix
        self.inputs.update(infile=infile, 
                           reference=reference,
                           outfile=outfile,
                           outmatrix = outmatrix)
        """
        newflirt.args.extend(['-in %s'%(newflirt.inputs.infile)])
        newflirt.infile = infile
        newflirt.args.extend(['-ref %s'%(newflirt.inputs.reference)])
        newflirt.reference = reference
        if newflirt.inputs.outfile:
            newflirt.args.extend(['-out %s'%(newflirt.inputs.outfile)])
            newflirt.outfile = outfile
        if newflirt.inputs.outmatrix:
            newflirt.args.extend(['-omat %s'%(newflirt.inputs.outmatrix)])
            newflirt.outmatrix = outmatrix
        """

        results = self._runner()
        if results.runtime.returncode == 0:
            results.outputs = self.aggregate_outputs()

        return results 
        

    def applyxfm(self, infile=None, reference=None, inmatrix=None, outfile=None):
        """ runs flirt command 
          eg.
          flirted = flirtter.applyxfm(self, infile=None, reference=None, inmatrix=None, outfile=None)
          flirt [options] -in <inputvol> -ref <refvol> -applyxfm -init <matrix> -out <outputvol>

        Parameters
        ----------
        infile : filename
            filename of volume to be moved
        reference : filename
            filename of volume used as target for registration
        inmatrix : filename  inmat.mat
            filename holding transformation matrix in asci format
        outfile : filename
            filename of new volume of infile moved to space of reference
            if None,  only the transformation matrix will be calculated

        Returns
        --------
        flirt : object
            return new flirt object with updated fields
        """
        #newflirt = self.update()
        if infile is None:
            if self.inputs.infile is None:
                raise ValueError('input not specfied')
            else:
                infile = self.inputs.infile
        if reference is None:
            if self.inputs.reference is None:
                raise ValueError('reference is not specified')
            else:
                reference = self.inputs.reference
        if outfile is None:
            if self.inputs.outfile is None:
                raise ValueError('outfile not specified')
            else:
                outfile = self.inputs.outfile
        if inmatrix is None:
            if self.inputs.inmatrix is None:
                raise ValueError('inmatrix is not specified')
            else:
                inmatrix = self.inputs.inmatrix
        self.inputs.update(infile=infile, 
                           reference=reference,
                           outfile=outfile,
                           inmatrix = inmatrix,
                           flags='-applyxfm')        
            
        results = self._runner()
        if results.runtime.returncode == 0:
            results.outputs = self.aggregate_outputs()
            
        return results 
        

        """newflirt.args.extend(['-in %s'%(infile)])
        newflirt.infile = infile
        
        newflirt.args.extend(['-ref %s'%(reference)])
        newflirt.reference = reference
        
        if newflirt.inputs.applyisoxfm is not None:
            newflirt.args.extend(['-applyisoxfm %d'%(newflirt.inputs['applyisoxfm'])])
            
        else:
            newflirt.args.extend(['-applyxfm'])
        
        newflirt.args.extend(['-init %s'%(inmatrix)])
        newflirt.inmatrix = inmatrix
        
        newflirt.args.extend(['-out %s'%(outfile)])
        newflirt.outfile = outfile
            
        (retcode, out, err) = newflirt._runner(newflirt.cmdline)
        newflirt.retcode = retcode
        newflirt.out = out
        newflirt.err = err
        
        return newflirt
        """

        



class Fnirt(CommandLine):

    @property
    def cmd(self):
        """sets base command, not editable"""
        return 'fnirt'

    def __init__(self, **inputs):
        """use fsl fnirt for non-linear registration
        
        Options
        -------
        see  
        fsl.Fnirt().inputs_help()
        
        Example
        -------
        >>> fnirter = fsl.Fnirt(affine='affine.mat')
        >>> fnirted = fnirter.run(reference='ref.nii',moving='anat.nii')
        >>> fsl.Fnirt().inputs_help()
       
       
        """
        super(Fnirt,self).__init__()
        self.args = []
        self._populate_inputs()
        self.inputs.update(**inputs)
        self.infile = ''
        self.reference = ''

    def inputs_help(self):
        doc = """

        POSSIBLE OPTIONS
        -----------------
        (all default to None and are unset)
 
        http://www.fmrib.ox.ac.uk/fsl/fnirt/index.html#fnirt_parameters

        Parameters Specifying Input Files
        +++++++++++++++++++++++++++++++++
        infile : <filename>
            file that gets moved/warped
            can be set at .run(infile='infile')
        reference : <filename>
            file that specifies set space that infile
            gets moved/warped to
            can be set at .run(reference='reference')
        affine : <filename>
            name of file containing affine transform
	initwarp : <filename>
            name of file containing initial non-linear warps
	initintensity : <filename>
      	    name of file/files containing initial intensity maping
	configfile : <filename> 
	    Name of config file specifying command line arguments
	referencemask : <filename>
	    name of file with mask in reference space
	imagemask : <filename>	
            name of file with mask in input image space

        Parameters Specifying Output Files
        ++++++++++++++++++++++++++++++++++
	fieldcoeff_file: <filename>
	    name of output file with field coefficients
	outimage : <filename>
	    name of output image
	fieldfile : <filename>
	    name of output file with field
	jacobianfile : <filename>
	    name of file for writing out the Jacobian of the field 
            (for diagnostic or VBM purposes)
	reffile : <filename>	
            name of file for writing out intensity modulated reference
            (for diagnostic purposes)
	intensityfile : <filename>
	    name of files for writing information pertaining to 
            intensity mapping
	logfile : <filename>
	    Name of log-file

        verbose	: Bool
            If True, Print diagonostic information while running

        Parameters Specified "Once and for All"
        +++++++++++++++++++++++++++++++++++++++
        jacobian_range : [float,float]	
            Allowed range of Jacobian determinants, (FSLdefault 0.01,100.0)
            [0.01,100] generally ensures diffeomorphism (mapping invertible, 
            and there is exactly one position V for each position in U 
            (with mapping U -> V)
            [-1] allows jacobians to take any value (pos or neg)
            [0.2,5] suggested for VBM where the Jacobians are used to modulate 
            tissue probabilities, otherwise may have non-normal distributions
	warp_resolution: list [10.0,10.0,10.0]
	    (approximate) resolution (in mm) of warp basis 
            in x-, y- and z-direction, (FSLdefault 10,10,10)
	splineorder : int
	    Order of spline, 2->Qadratic spline, 3->Cubic spline. 
            (FSLDefault=3)
	implicit_refmask : Bool
	    If =True, use implicit masking based on value in --ref image. 
            (FSLDefault =1; True)
            Specifies a value implying that we are outside the valid FOV. 
            Typically that value will be zero, otherwise use
            implicit_refmaskval to specify other value  . 
            Occasionally a software will use some other value eg(NaN, 1024) 
	implicit_imgmask : Bool
	    If =1, use implicit masking based on value in --in image, 
            (FSLDefault =1; True) See explanation for implicit_refmask above
	implicit_refmaskval : float
	    Value to mask out in --ref image. FSLDefault =0.0
	implicit_imgmaskval : float
	    Value to mask out in --in image. FSLDefault =0.0
        ssqlambda : Bool	
            If True (=1), lambda is weighted by current sum of squares
            (FSLdefault =True), helps avoid solutions getting caught in 
            local minima
        regularization_model : string  {'membrane_energy', 'bending_energy'}
	    Model for regularisation of warp-field, 
            (FSLdefault 'bending_energy')
            Helps keep points close together in original image,
            close together in the warped image
        refderiv : Bool
 	    If True (1), reference image is used to calculate derivatives. 
            (FSLDefault = 0 ; False) Limited applicability
        intensity_model : string {'none', 'global_linear', 'global_non_linear',
            'local_linear', 'global_non_linear_with_bias', 'local_non_linear'}	
            Model for intensity-mapping: The purpose is to model intensity 
            differences between reference and image to avoid these affecting 
            the estimation of the warps. Modelling the intensity involves 
            extra estimation parameters (in addition to modelling the warps) 
            and willincrease both execution time and memory requirements. 
        intorder : int 	
            Determines the order of a polynomial that models a curvilinear 
            relationship between the intensities in (reference, image)
            (FSLdefault =  5)
        bias_resolution: [int, int, int]
            Determines the knot-spacing for splines used to model a bias-field.
            Relevant for intensity_models {'local_linear', 
            'global_non_linear_with_bias','local_non_linear'} 
            (FSLdefault=[50,50,50])
        bias_lambda : int
            Determines relative weight of sum-of-squared differences and  
            bending energy of the bias-field. Similar to the lambda paramter, 
            but for the bias-field rather than the warp-fields. 
            (FSLDefault is 10000) 
        hessian_datatype : string {'double', 'float'}
	    Precision for representing Hessian, Changing to float decreases
            amount of RAM needed to store Hessian allowing slightly higher 
            warp-resolution. Double used for most testing and validation 
            (FSL default = 'double') 

        Parameters Specified Once for each Sub-Sampling Level
        +++++++++++++++++++++++++++++++++++++++++++++++++++++
        Fnirt uses a multi-resolution, subsampling approach to
        identify best warps, starting at a coarse level, refining at
        higher resolutions.
        These parameters need to be set for each level 
        (typically 3 levels are used; greater levels = greater processing time)

        sub_sampling : list [4,2,1] 
	    sub-sampling scheme, default 4,2,1
            means image will be upsampled (factor of 4) at level one,
            upsampled (factor of 2) at level two, and
            then (full resolution) at level three
        max_iter : list [5,5,5]
	    Maximum number of non-linear iterations, at each level
            (FSLdefault 5,5,5)
	referencefwhm : list [4,2,1]
	    FWHM (in mm) of gaussian smoothing kernel for ref volume, 
            Smoothing should mirror sub_sampling
            sub_sampling = [4,2,1], referencefwhm = [8,4,1]
            (FSLdefault 4,2,0,0) reference often smooth, so can be less than image
	imgfwhm : list [6.0,4.0,2.0,2.0]
	    FWHM (in mm) of gaussian smoothing kernel for input volume, 
            Smoothing should mirror sub_sampling
            sub_sampling = [4,2,1], imgfwhm = [10,6,2]
            (FSLdefault 6,4,2,2)
	lambdas : list [300, 75, 30]
            Specifies relative weighting of the sum-of-squared differences 
            and the regularisation (smoothness) of the warps.
            FSLdefault depends on ssqlambda and regularization_model switches.
            Different "types" of data require different values
            You can specify **one** value, but best to modulate with 
            sub_sampling
        estintensity : list [1,1,0]
            Determines if the parameters of the chosen intesity-model should be 
            estimated at each level if intensity_model is not None
            eg [1,1,0] Estimates at first two levels but not at last level
            assuming estimates at that level are fairly correct
        applyrefmask : list [1,1,1]
	    Use specified refmask at each level
            (FSLdefault 1 (true)) eg [0,0,1] to not use brain mask for 
            initial coarse level registration, as extra-cranial tissue may
            provide information useful at initial steps
	applyimgmask : list [1,1,1]
	    Use specified imagemask at each level
            (FSLdefault 1 (true)) eg [0,0,1] to not use brain mask for 
            initial coarse level registration, as extra-cranial tissue may
            provide information useful at initial steps
        """
        print doc
    def _populate_inputs(self):
        self.inputs = Bunch(infile=None,
                          reference=None,
                          affine=None,
                          initwarp= None,
                          initintensity=None,
                          configfile=None,
                          referencemask=None,
                          imagemask=None,
                          fieldcoeff_file=None,
                          outimage=None,
                          fieldfile=None,
                          jacobianfile=None,
                          reffile=None,
                          intensityfile=None,
                          logfile=None,
                          verbose=None,
                          sub_sampling=None,
                          max_iter=None,
                          referencefwhm=None,
                          imgfwhm=None,
                          lambdas=None,
                          estintensity=None,
                          applyrefmask=None,
                          applyimgmask=None)

    def _parse_inputs(self):
        """validate fsl bet options
        if set to None ignore
        """
        out_inputs = []
        inputs = {}
        [inputs.update({k:v}) for k, v in self.inputs.iteritems() if v is not None ]
        for opt in inputs:
            if opt in ['infile', 'reference']:
                continue
            if opt is 'affine':
                val = inputs[opt]
                out_inputs.extend(['--aff %s'%(val)])
                continue
            if opt is 'initwarp':
                val = inputs[opt]
                out_inputs.extend(['--inwarp %s'%(val)])
                continue                
            if opt is 'initintensity':
                val = inputs[opt]
                out_inputs.extend(['--intin %s'%(val)])
                continue
            if opt is 'configfile':
                val = inputs[opt]
                out_inputs.extend(['--config %s'%(val)])
                continue
            if opt is 'referencemask':
                val = inputs[opt]
                out_inputs.extend(['--refmask %s'%(val)])
                continue
            if opt is 'imagemask':
                val = inputs[opt]
                out_inputs.extend(['--inmask %s'%(val)])
                continue
            if opt is 'fieldcoeff_file':
                val = inputs[opt]
                out_inputs.extend(['--cout %s'%(val)])
                continue
            if opt is 'outimage':
                val = inputs[opt]
                out_inputs.extend(['--iout %s'%(val)])
                continue
            if opt is 'fieldfile':
                val = inputs[opt]
                out_inputs.extend(['--fout %s'%(val)])
                continue
            if opt is 'jacobianfile':
                val = inputs[opt]
                out_inputs.extend(['--jout %s'%(val)])
                continue
            if opt is 'reffile':
                val = inputs[opt]
                out_inputs.extend(['--refout %s'%(val)])
                continue
            if opt is 'intensityfile':
                val = inputs[opt]
                out_inputs.extend(['--intout %s'%(val)])
                continue
            if opt is 'logfile':
                val = inputs[opt]
                out_inputs.extend(['--logout %s'%(val)])
                continue
            if opt is 'verbose':
                if inputs[opt]:
                    out_inputs.extend(['--verbose'])
                continue
            if opt is 'sub_sampling':
                val = inputs[opt]
                tmpstr = '--subsample '
                for item in val:
                    tmpstr = tmpstr + '%d, '%(item)
                out_inputs.extend([tmpstr[:-2]])
                continue
            if opt is 'max_iter':
                val = inputs[opt]
                tmpstr = '--miter '
                for item in val:
                    tmpstr = tmpstr + '%d, '%(item)
                out_inputs.extend([tmpstr[:-2]])
                continue               
            if opt is 'referencefwhm':
                val = inputs[opt]
                tmpstr = '--reffwhm '
                for item in val:
                    tmpstr = tmpstr + '%d, '%(item)
                out_inputs.extend([tmpstr[:-2]])
                continue
            if opt is 'imgfwhm':
                val = inputs[opt]
                tmpstr = '--infwhm '
                for item in val:
                    tmpstr = tmpstr + '%d, '%(item)
                out_inputs.extend([tmpstr[:-2]])
                continue
            if opt is 'lambdas':
                val = inputs[opt]
                tmpstr = '--lambda '
                for item in val:
                    tmpstr = tmpstr + '%d, '%(item)
                out_inputs.extend([tmpstr[:-2]])
                continue
            if opt is 'estintensity':
                val = inputs[opt]
                tmpstr = '--estint '
                for item in val:
                    tmpstr = tmpstr + '%d, '%(item)
                out_inputs.extend([tmpstr[:-2]])
                continue
            if opt is 'applyrefmask':
                val = inputs[opt]
                tmpstr = '--applyrefmask '
                for item in val:
                    tmpstr = tmpstr + '%d, '%(item)
                out_inputs.extend([tmpstr[:-2]])
                continue
            if opt is 'applyimgmask':
                val = inputs[opt]
                tmpstr = '--applyinmask '
                for item in val:
                    tmpstr = tmpstr + '%d, '%(item)
                out_inputs.extend([tmpstr[:-2]])
                continue
            if opt is 'flags':
                out_inputs.extend(inputs[opt])
                continue
            print 'option %s not supported'%(opt)
        return out_inputs
            
    @property
    def cmdline(self):
        """validates fsl options and generates command line argument"""
        valid_inputs = self._parse_inputs()
        allargs = self.args + valid_inputs
        return ' '.join(allargs)
  
    def run(self, infile=None, reference=None):
        """ runs fnirt command
         

        Parameters
        ----------
        infile : filename
            filename of volume to be warped/moved
        reference : filename
            filename of volume used as target for  warp registration

        Returns
        --------
        fnirt : object
            return new fnirt object with updated fields

        Examples
        --------
        >>> #T1-> MNI153
        >>>fnirt_mprage = fsl.Fnirt(imgfwhm=[8,4,2],sub_sampling=[4,2,1],
                                   warp_resolution=[6,6,6])
        >>>fnirted_mprage = fnirt_mprage.run(infile='jnkT1.nii', reference='refimg.nii')
        """
        #newfnirt = self.update()
        if infile is None:
            if self.inputs.infile is None:
                raise ValueError('infile is not specified')
            else:
                infile = self.inputs.infile
        if reference is None:
            if self.inputs.reference is None:
                raise ValueError('reference is not specified')
            else:
                reference = self.inputs.reference
        newfnirt = self.update(infile=infile, reference=reference)
        newfnirt.args.extend(['--in %s'%(infile)])
        newfnirt.infile = infile
        newfnirt.args.extend(['--ref %s'%(reference)])
        newfnirt.reference = reference
        
        
        (retcode, out, err) = newfnirt._runner(newfnirt.cmdline)
        newfnirt.retcode = retcode
        newfnirt.out = out
        newfnirt.err = err
        
        return newfnirt

    @property
    def cmdline(self):
        """validates fsl options and generates command line argument"""
        valid_inputs = self._parse_inputs()
        
        if valid_inputs is None:
            allargs = [self.cmd] + self.args
        else:
            allargs = [self.cmd] + valid_inputs + self.args
        return ' '.join(allargs)

    def update(self, **inputs):
        newfnirt = Fnirt()
        [newfnirt.inputs.__setattr__(k,v) for k, v in self.inputs.iteritems() if v is not None ]
        newfnirt.inputs.update(**inputs)
        return newfnirt

    def write_config(self,configfile):
        """Writes out currently set options to specified config file
        
        Parameters
        ----------
        configfile : /path/to/configfile

                
        """
        valid_inputs = self._parse_inputs() 
        try :
            fid = fopen(configfile, 'w+')
        except IOError:
            print ('unable to create config_file %s'%(configfile))
            
        for item in valid_inputs:
            fid.write('%s\n'%(item))
        fid.close()




class FSFmaker:
    '''Use the template variables above to construct fsf files for feat.
    
    This doesn't actually run anything.
    
    Example usage
    -------------
    FSFmaker(5, ['left', 'right', 'both'])
        
    '''
    # These are still somewhat specific to my experiment, but should be so in an
    # obvious way.  Contrasts in particular need to be addressed more generally.
    # These should perhaps be redone with a setattr_on_read property, though we
    # don't want to reload for each instance separately.
    fsf_header = load_template('feat_header.tcl')
    fsf_ev = load_template('feat_ev.tcl')
    fsf_ev_ortho = load_template('feat_ev_ortho.tcl')
    fsf_contrasts = load_template('feat_contrasts.tcl')

    def __init__(self, num_scans, cond_names):
        subj_dir = dirname(getcwd())
        # This is more package general, and should happen at a higher level
        fsl_root = getenv('FSLDIR')
        for i in range(num_scans):
            fsf_txt = self.fsf_header.substitute(num_evs=len(cond_names), 
                                                 base_dir=subj_dir, scan_num=i,
                                                 fsl_root=fsl_root)
            for j, cond in enumerate(cond_names):
                fsf_txt += self.gen_ev(i, j+1, cond, subj_dir, len(cond_names))
            fsf_txt += self.fsf_contrasts.substitute()

            f = open('scan%d.fsf' % i, 'w')
            f.write(fsf_txt)
            f.close()
                
                
    def gen_ev(self, scan, cond_num, cond_name, subj_dir, total_conds):
        args = (cond_num, cond_name) + (cond_num,) * 6 + \
                (scan, cond_name) + (cond_num, ) * 2

        ev_txt = self.fsf_ev.substitute(ev_num=cond_num, ev_name=cond_name,
                                        scan_num=scan, base_dir=subj_dir)

        for i in range(total_conds + 1):
            ev_txt += self.fsf_ev_ortho.substitute(c0=cond_num, c1=i) 

        return ev_txt


##################################################################################


    
    
#def bet(*args, **kwargs):
#   bet_element = BetElement(*args, **kwargs)
    
    # We should check the return value
#    bet_element.execute()

#    return load_image(bet_element.state['output'])

#def flirt(target, moving, space=None, output_filename=None, **kwargs):
"""Call flirt to register moving to target with optional space to define 
    space new image is resliced into

    Parameters
    ----------

    target : nipy image
        Image to register other image(s) to
    moving : nipy image
        Image being moved/registered to target
    space : nipy image or coordinate_map
        image or coordinate map defining space to reslice image into
    outputfilename  : filename
        optional filename to use when creating registered image

    Returns
    -------

    movedimage : nipy image
        Image coregistered to target

    transform : numpy array
        A 4 X 4 array os the transform from moving to target

    Other Parameters
    ----------------
    xform_only : True
        Only computes the transform and only returns transform
"""
#    target_filename = target.filename

    
def apply_transform(target, moving, transform, space=None, output_filename=None):
    """
    While this also uses flirt, it is a quite different usage, and as such gets
    it's own function.
    """
    pass

if __name__ == '__main__':
    fastin = FastInputs()
    fastin.configure_traits()
    print fastin.get()
