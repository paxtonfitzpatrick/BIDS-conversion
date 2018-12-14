import os
import shutil
from datetime import date

def bidsify(origpath, destpath, n_sessions=2, scan_types=None, scan_names=None, log_changes=True, log_name='CHANGES', verbose=False):

    """
    Copies files and reorganizes directory structure to comply with BIDS convention

    Parameters
    ----------
    origpath : str
        Path to directory of files to be BIDSified

    destpath : str
        Path to desired output directory for BIDS-formatted files. The directory
        does not have to exist prior to running in order to work

    n_sessions : int
        Number of different scan each participant attended (usually on separate
        days). Default is 2.

    scan_types : list of strings
        Names of scan types (and other directories) for organizing within subject
        directories. Default is ['anat','func','log'] for anatomical and functional
        scan folders, and a folder for changelog files.

    scan_names : dict
        Custom mapping betweeen current file names (keys) and desired output
        file names (values). Default is:
            {'mprage' : 'T1w',
            'bold1' : 'task-rest_run-01_bold',
            'bold2' : 'task-mcr_run-02_bold',
            'bold3' : 'task-swm_run-03_bold',
            'bold4' : 'task-dd_run-04_bold',
            'bold5' : 'task-rest_run-05_bold'}

    log_changes : bool
        If True, create a .log file noting the moving and renaming of files and
        the current date, named according to log_name. Default is True.

    log_name : str
        Name of output .log file. Default is 'CHANGES' (BIDS-specified name).

    verbose : bool
        If True, print progress updates while running, after each file is moved
        and renamed. Default is False.

    """

        # convert to absolute paths if relative path is passed
    origpath_abs = os.path.abspath(origpath)
    destpath_abs = os.path.abspath(destpath)

    # instantiate list of unsuccessfully handled file paths
    problem_files = []

    if scan_types is None:
        scan_types = ['anat','func','log']

    if scan_names is None:
        # use default dictionary of scan types
        scan_names = {
            'mprage' : 'T1w',
            'bold1' : 'task-rest_run-01_bold',
            'bold2' : 'task-mcr_run-02_bold',
            'bold3' : 'task-swm_run-03_bold',
            'bold4' : 'task-dd_run-04_bold',
            'bold5' : 'task-rest_run-05_bold'
        }

    # Handles changing file names during move
    def rename(file, root, n_sessions, scan_names, destpath_abs, log_changes, log_name, verbose):

        # viarable to track unsuccessfully renamed files
        problem_file = None

        old_path = os.path.join(root, file)
        base, ext = os.path.splitext(file)
        splitpath = root.split('/')

        # get subject ID
        sub = splitpath[-2].split('_')[0]

        # get session number
        ses_number = splitpath[-2].split('_')[1]
        if int(ses_number) <= n_sessions:
            session = 'ses-'+ses_number

        else:
            print('unrecognized session number \'' + ses_number + '\' for subID ' + sub)
            problem_file = file

        # get scan type (or log)
        if splitpath[-1] == 'ANATOMY':
            runtype = 'anat'

        elif splitpath[-1] == 'FUNCTIONAL':
            runtype = 'func'

        elif splitpath[-1] == 'LOG':
            runtype = 'LOG'

        else:
            print('unrecognized scan or log folder ' + splitpath[-1] + ' for subID ' + sub)
            problem_file = file

        # format scan name (or preserve name of log file)
        if base in scan_names:
            new_name = scan_names[base]

        elif ext =='.log':
            new_name = base

        else:
            print('unrecognized scan name ' + base + ' for file ' + file)
            problem_file = file

        try:
            if runtype != 'LOG':
                new_path = os.path.join(destpath_abs, sub, session, runtype, sub+'_'+new_name+ext)
            else:
                new_path = os.path.join(destpath_abs, sub, session, runtype, new_name+ext)

            if log_changes:
                writelog(log_name, old_path, destpath_abs, sub, session, new_name, ext, verbose)

        except NameError:
            new_path = None


        return new_path, problem_file

    # writes/updates log of moving and renaming file
    def writelog(log_name, old_path, destpath_abs, sub, session, new_name, ext, verbose):

        filename = os.path.join(destpath_abs, sub, session, 'LOG', log_name + '.log')

        if os.path.exists(filename):
            mode = 'a'

        else:
            mode = 'w'

        with open(filename, mode) as f:
            f.write(
                date.today().strftime('%Y-%m-%d') + '\n' +
                ' - ' + new_name+ext + ' moved from ' + old_path + '\n'
            )

        if verbose:
            print('wrote to log file ' + filename)


    for i, (root, dirs, files) in enumerate(os.walk(origpath_abs)):
        # create new directory structure
        if i == 0:
            [os.makedirs(destpath_abs+'/'+direc.split('_')[0]+'/ses-'+str(ses+1)+'/'+scantype, exist_ok=True) for direc in dirs for scantype in scan_types for ses in range(n_sessions)]

        # move and rename files
        else:
            file_list = [f for f in files if not f.startswith('.')]
            if file_list:
                for file in file_list:
                    old_filepath = os.path.join(root, file)
                    new_filepath, problem_file = rename(file, root, n_sessions, scan_names, destpath_abs, log_changes, verbose)

                    if new_filepath is not None:
                        # move and rename
                        shutil.copy(old_filepath, new_filepath)

                        if verbose:
                            print('moved ' + old_filepath + ' to ' + new_filepath)

                    else:
                        problem_files.append(problem_file)


                    if problem_files:
                        print('The following files were not successfully converted: ' + problem_files)
