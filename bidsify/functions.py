import os
import shutil
from datetime import date


def bidsify(origpath, destpath, n_sessions=2, scan_types=None, detect_size=True, log_changes=True, log_name='CHANGES',
            log_errors=True, errlog_path = None, verbose=True):

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

    detect_size : bool
        If True, do name mapping logic based on expected file size for each file
        type. Default is True.

    log_changes : bool
        If True, create a .log file within each scan type folder noting the moving
        and renaming of files and the current date, named according to log_name.
        Default is True.

    log_name : str
        Name of output .log files. Default is 'CHANGES' (BIDS-specified name).

    log_errors : bool
        If True, create a .log file noting any files not correctly renamed and moved.
        If False, print the notes to the screen instead. Default is True.

    errlog_path : str
        Path to desired output directory for error log file. Default is the current
        directory.

    verbose : bool
        If True, print progress updates while running, after each file is moved
        and renamed. Default is True.

    """


    # convert to absolute paths if relative path is passed
    origpath_abs = os.path.abspath(os.path.expanduser(origpath))
    destpath_abs = os.path.abspath(os.path.expanduser(destpath))

    # dict to hold unsuccessfully handled files with errors
    problem_files = {}

    # default output folder names
    if scan_types is None:
        scan_types = ['anat','func','log']

    # for name mapping based on file size
    if detect_size:    #and scan_names is None:
        method = 'size'
    else:
        raise ValueError('detect_size must be True. Mapping by other file attributes not currently supported.')

    # set path for output of renaming error log file
    if log_errors:
        if errlog_path is None:
            errlog_path = os.path.abspath(os.path.curdir)
        else:
            errlog_path = os.path.abspath(os.path.expanduser(errlog_path))

    for i, (root, dirs, files) in enumerate(os.walk(origpath_abs, topdown=True)):

        # do not recurse into the 'DONTUSE' folder
        dirs[:] = [d for d in dirs if not d.startswith('DONTUSE')]

        # create new directory structure
        if i == 0:
            if verbose:
                print('Creating BIDS directory structure...')
            [os.makedirs(destpath_abs+'/sub-'+direc.split('_')[0]+'/ses-'+str(ses+1)+'/'+scantype, exist_ok=True) for \
             direc in dirs for scantype in scan_types for ses in range(n_sessions)]

        # move and rename files
        file_list = [f for f in files if not f.startswith('.')]
        if file_list:

            # store subject ID & session number
            splitroot = root.split('/')
            sub, ses = 'sub-'+splitroot[-2].split('_')[0], splitroot[-2].split('_')[1].lstrip('0')

            # for name mapping based on file size
            if method == 'size':
                path_map, prob_fs = _rename_size(file_list, splitroot, sub, ses, n_sessions, destpath_abs,
                                                 log_changes, log_name, verbose)

                for old_filepath, new_filepath in path_map.items():
                    if verbose:
                        print('moving ' + old_filepath + ' to ' + new_filepath + ' ...')
                    shutil.copy(old_filepath, new_filepath)

                # store problems with subject folder by ID & session number
                if prob_fs:
                    if sub not in problem_files:
                        problem_files.update({sub : {ses : prob_fs}})
                    else:
                        problem_files[sub].update({ses : prob_fs})

    print('------------------------')
    if problem_files and log_errors:
        if verbose:
            print('Writing error log file')
        _write_errorlog(problem_files, errlog_path)
        print('Finished.\nBIDSified directory output at ' + destpath_abs + '\nSee ' +
              os.path.join(errlog_path, 'bidsify_errors.log') + ' for log of encountered errors.')

    elif problem_files and not log_errors:
        _print_errorlog(problem_files)
        print('Finished.\nBIDSified directory output at ' + destpath_abs +
              '\nSee above for list of encountered errors.')

    elif not problem_files and log_errors:
        print('Finished.\nBIDSified directory output at ' + destpath_abs +
              '\nNo conversion errors encountered, so error log file not written.')

    else:
        print('Finished.\nBIDSified directory output at ' + destpath_abs)


def _rename_size(file_list, splitroot, sub, ses, n_sessions, destpath_abs, log_changes, log_name, verbose):

    """ Defines naming scheme for files based on size """

    old_fps = [os.path.join(os.sep,*splitroot,file) for file in file_list]
    path_maps = dict.fromkeys(old_fps)
    sizes_dict = {file: os.stat(file).st_size for file in old_fps}
    prob_fs = {}

    # get session number
    if int(ses) <= int(n_sessions):
        session = 'ses-'+ses

    else:
        prob_fs['Session ?']= 'Unrecognized session number: ' + ses
        return path_maps, prob_fs


    # deal with anatomical scans
    if splitroot[-1] == 'ANATOMY':
        # expected size for mprage files (bytes)
        right_size = 28836192
        # use file that matches expected size, or if none do, use one closest to expected size
        if right_size in sizes_dict.values():
            best_scan = [k for k, v in sizes_dict.items() if v == right_size][-1]
        else:
            best_scan = \
            [k for k, v in sizes_dict.items() if v == min(sizes_dict.items(), key=lambda x: abs(right_size - x[1]))[1]][
                -1]
            prob_fs[best_scan.split('/')[-1]] = 'No mprage of expected size. Used closest match: ' + \
                                                best_scan.split('/')[-1]

        new_name = 'T1w.nii'
        path_maps[best_scan] = os.path.join(destpath_abs, sub, session, 'anat', sub+'_'+session+'_'+'_acq-MPRAGE_T1w.nii')

    # deal with functional scans
    elif splitroot[-1] == 'FUNCTIONAL':
        rests = []
        mcrs = []
        swms = []
        leftovers = []
        for old_file, size in sizes_dict.items():
            # expected size of resting state scan (+/- 2kb)
            if size in range(110590352, 110594352):
                rests.append(old_file)

            # expected size of mcr scan (+/- 2kb)
            elif size in range(77412752, 77416752):
                mcrs.append(old_file)

            # expected size of swm scan (+/- 2kb)
            elif size in range(82942352, 82946352):
                swms.append(old_file)
            else:
                leftovers.append(old_file)

        # map resting state scans
        if not rests:
            prob_fs['Resting state'] = 'No scan files matching expected size for Resting State.'

        elif len(rests) == 1:
            prob_fs['Resting state'] = 'Unable to determine which Resting State scan for file: ' + rests[0]

        elif len(rests) == 2:
            rest1, rest2 = sorted(rests)[0], sorted(rests)[1]
            path_maps[rest1] = os.path.join(destpath_abs, sub, session, 'func', sub+'_task-rest_run-01_bold.nii')
            path_maps[rest2] = os.path.join(destpath_abs, sub, session, 'func', sub+'_task-rest_run-05_bold.nii')
        else:
            prob_fs['Resting state'] = 'Unable to identify Resting State 1 vs 2 from choices: ' + rests[0]

        # map mcr scans
        if mcrs:
            path_maps[mcrs[-1]] = os.path.join(destpath_abs, sub, session, 'func', sub+'_task-mcr_run-02_bold.nii')
        else:
            prob_fs['MCR'] = 'No scan files matching expected size for MCR'

        # map swm scans
        if swms:
            path_maps[swms[-1]] = os.path.join(destpath_abs, sub, session, 'func', sub+'_task-swm_run-03_bold.nii')
        else:
            prob_fs['SWM'] = 'No scan files matching expected size for SWM'

        if len(leftovers) == 1:
            path_maps[leftovers[0]] = os.path.join(destpath_abs, sub, session, 'func', sub+'_task-dd_run-04_bold.nii')
        else:
            prob_fs['DD'] = 'Unable to identify DD scan from choices: ' + str(leftovers)

    # deal with log files
    elif splitroot[-1] == 'LOG':
        runtype = 'LOG'
        # keep existing name
        for file in old_fps:
            path_maps[file] = os.path.join(destpath_abs, sub, session, 'log', file.split('/')[-1])

    else:
        prob_fs[''] = 'unrecognized scan or log folder: ' + splitroot[-1]
        return path_maps, prob_fs

    # note any scan files not mapped...
    unmapped = [old_file for old_file, new_file in path_maps.items() if not new_file]
    if unmapped:
        prob_fs['Unmapped files'] = 'The following files were not moved and renamed: ' + str(unmapped)

    # ...and filter them from the dictionary
    filtered_path_maps = {k: v for k, v in path_maps.items() if v is not None}

    # create & write log file in destination dir with record of move
    if log_changes:
        _write_changelog(log_name, filtered_path_maps, destpath_abs, sub, session, verbose)

    return filtered_path_maps, prob_fs


def _write_changelog(log_name, path_maps, destpath_abs, sub, session, verbose):

    """ Writes/updates log of moving file """

    filename = os.path.join(destpath_abs, sub, session, 'log', log_name + '.log')

    with open(filename, 'a') as f:
        f.write(date.today().strftime('%Y-%m-%d') + '\n')
        for old_path, new_path in path_maps.items():
            f.write('- ' + new_path + ' moved from ' + old_path + '\n')

    if verbose:
        print('wrote to log file ' + filename)


def _write_errorlog(problem_files, errlog_path):

    """ Writes log file containing errors in renaming/moving files """

    filename = os.path.join(errlog_path, 'bidsify_errors.log')

    with open(filename, 'a') as f:
        f.write('BIDSIFY FILE CONVERSION ERRORS:\n')

        for sub, ses in problem_files.items():
            f.write('\n'+sub+'\n')
            for ses, errs in ses.items():
                f.write('\tsession ' + ses + ':\n')
                for k,v in errs.items():
                    f.write('\t\t' + k + ': ' + str(v) + '\n')


def _print_errorlog(problem_files):

    """ Prints errors in renaming/moving files """

    for sub, ses in problem_files.items():
        print(sub)
        for ses, errs in ses.items():
            print('\tsession ' + ses + ':')
            for k,v in errs.items():
                print('\t\t' + k + ': ' + str(v))
