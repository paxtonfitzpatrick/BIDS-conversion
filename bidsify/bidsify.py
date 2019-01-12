import argparse
from functions import bidsify

parser = argparse.ArgumentParser(description='Convert data to BIDS format')
parser.add_argument('origpath', type=str, help='Path to directory of files to be BIDSified')
parser.add_argument('destpath', type=str, help='Path to output directory for BIDSified files.')
parser.add_argument('--n_sessions', default=2, type=int, help='Number of different scan each participant attended.')
parser.add_argument('--scan_types', default=None, help='Names of scan types (and other directories) for organizing '
                                                       'within subject directories.')
parser.add_argument('--detect_size', action='store_false', help='Use expected file sizes to map between old and new '
                                                                'naming schemes.')
parser.add_argument('--log_changes', action='store_false', help='Create a .log file in each scan type folder noting '
                                                                'the moving and renaming of files and the current '
                                                                'date, named according to --log_name.')
parser.add_argument('--log_errors', action='store_false', help='Create a .log file noting any files not correctly '
                                                               'renamed and moved.')
parser.add_argument('--errlog_path', default=None, type=str, help='Path to desired output directory for error log file.')
parser.add_argument('--log_name', default='CHANGES', type=str, help='Name of output .log file.')
parser.add_argument('--verbose', action='store_false', help='Print progress updates while running, after each file is '
                                                            'moved and renamed.')

args = parser.parse_args()

bidsify(args.origpath, args.destpath, args.n_sessions, args.scan_types, args.detect_size, args.log_changes,
        args.log_name, args.log_errors, args.errlog_path, args.verbose)
