import pysftp
import argparse
import os
from datetime import datetime
from typing import Dict, Tuple, List

RESOURCES_DIR = 'resources'

def parse_filename (path: str) -> Tuple[str, str]:
    filename, _ = os.path.splitext(os.path.basename(path))
    arr = filename.split('_')
    try:
        return arr[0], arr[1]
    except IndexError:
        return arr[0], ''

def get_grid_dir_map (listing: List[str]) -> Dict[str, str]:
    dic = {}
    for i in listing:
       grid, timestamp = parse_filename(i)
       dic[grid] = i
    return dic

def compare_str_lists (a, b) -> bool:
    for x in a:
        if x not in b:
            return False
    for x in b:
        if x not in a:
            return False
    return True

def resources_match (sftp, local_path: str) -> bool:
    l_listing = os.listdir(local_path)
    r_listing = []
    with sftp.cd(RESOURCES_DIR):
        r_listing = sftp.listdir()
    return compare_str_lists(r_listing, l_listing)

def log(verbose):
    def vlog(*args):
        if verbose:
            print(*args)
    return vlog

def go (args, vlog) -> None:
    paths = os.listdir(args.dir)
    with pysftp.Connection(args.host, username=args.user, password=args.password, port=args.P) as sftp:
        # Batch profile places all folders of releases into a "batch" folder
        batch_dir = datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]
        root_dir = os.path.join(args.target_dir, batch_dir) if args.batch_profile else args.target_dir

        if args.batch_profile:
            vlog('>> Creating batch root directory %s' % (batch_dir))
            sftp.makedirs(root_dir)

        with sftp.cd(root_dir):
            remote_map = get_grid_dir_map(sftp.listdir())
            manifest_path = None
            for index, path in enumerate(paths):
                filename = os.path.basename(path)
                if filename[0] == '.':
                    continue
                if 'BatchComplete' in filename:
                    # Manifest file must be sent last.
                    manifest_path = os.path.abspath(os.path.join(args.dir, path))
                    continue
                vlog('Working on %s' % (filename,))
                grid, timestamp = parse_filename(filename)
                xml_name = grid + '.xml'
                l_xml_path = os.path.abspath(os.path.join(args.dir, path, xml_name))
                l_rdir_path = os.path.abspath(os.path.join(args.dir, path, RESOURCES_DIR))
                # Renames timestamp directories to the local copy.
                old_filename = remote_map.get(grid, '')
                if args.update_timestamps and old_filename and old_filename != filename:
                    vlog('>> Renaming %s to %s' % (old_filename, filename))
                    sftp.rename(old_filename, filename)
                if not sftp.exists(filename):
                    vlog('>> Creating directory %s' % (filename))
                    sftp.mkdir(filename)
                with sftp.cd(filename):
                    if not sftp.exists(RESOURCES_DIR):
                        vlog('>> Creating directory %s/%s' % (filename, RESOURCES_DIR))
                        sftp.mkdir(RESOURCES_DIR)
                    if args.skip_resources or (args.skip_matching_resources and resources_match(sftp, l_rdir_path)):
                        vlog('>> Skipping resource files')
                    else:
                        vlog('>> Uploading resource files')
                        sftp.put_d(l_rdir_path, RESOURCES_DIR, preserve_mtime=False)
                    if not args.skip_existing:
                        vlog('>> Uploading XML file')
                        sftp.put(l_xml_path, preserve_mtime=False)
            if args.batch_profile and manifest_path:
                vlog('>> Upload manifest file %s' % (manifest_path))
                sftp.put(manifest_path, preserve_mtime=False)

parser = argparse.ArgumentParser(description='Manages transfering DDEX files to a remote location.')
parser.add_argument('host',
        help='The SFTP host address')
parser.add_argument('--username',
        default='',
        dest='user',
        help='The SFTP username.')
parser.add_argument('--password',
        default='',
        help='The SFTP password.')
parser.add_argument('-P',
        default=22,
        type=int,
        help='Port.')
parser.add_argument('dir',
        help='The location of the release directories to upload.')
parser.add_argument('-v', '--verbose',
        dest='verbose',
        action='store_true',
        help='This flag enables the printing of information during the process.')
parser.add_argument('--update-timestamps',
        dest='update_timestamps',
        action='store_true',
        help='Indicates that previous timestamped files should be renamed.')
parser.add_argument('--batch-profile',
        dest='batch_profile',
        action='store_true',
        help='Indicates upload using ERN Choreography Batch profile instead of Release By Release Profile.')
parser.add_argument('--target-dir',
        dest='target_dir',
        default='upload',
        help='Allows you to change the designated directory to upload to.')
parser.add_argument('--skip-existing',
        dest='skip_existing',
        action='store_true',
        help='This flag indicates to not upload the DDEX XML notice.')
parser.add_argument('--skip-resources',
        dest='skip_resources',
        action='store_true',
        help='This flag indicates to not upload the resources directory.')
parser.add_argument('--skip-matching-resources',
        dest='skip_matching_resources',
        action='store_true',
        help='If the resource directory\'s files look the same it will be skipped.')
args = parser.parse_args()
go(args, log(args.verbose))
