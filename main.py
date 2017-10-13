import pysftp
import argparse
import os
from typing import Dict, Tuple, List

RESOURCES_DIR = 'resources'

def parse_filename (path: str):
    filename, _ = os.path.splitext(os.path.basename(path))
    arr = filename.split('_') 
    return arr[0], arr[1]

def get_grid_dir_map (listing: List[str]) -> Dict[str, str]:
    dic = {}
    for i in listing:
       grid, timestamp = parse_filename(i)
       dic[grid] = i
    return dic

def send_releases (args):
    paths = os.listdir(args.dir)
    with pysftp.Connection(args.host, username=args.user, password=args.password) as sftp:
        with sftp.cd(args.target_dir):
            remote_map = get_grid_dir_map(sftp.listdir())
            for index, path in enumerate(paths):
                filename = os.path.basename(path)
                if args.verbose: print('Working on %s' % (filename,))
                grid, timestamp = parse_filename(filename)
                xml_name = grid + '.xml'
                l_xml_path = os.path.abspath(os.path.join(args.dir, path, xml_name))
                l_rdir_path = os.path.abspath(os.path.join(args.dir, path, RESOURCES_DIR))
                # Renames timestamp directories to the local copy.                
                if args.update_timestamps and len(remote_map.get(grid, '')) > 0:
                    old_filename = remote_map.get(grid)
                    if args.verbose: print('>> Renaming %s to %s' % (old_filename, filename))
                    if not args.dry: sftp.rename(old_filename, filename)
                if not sftp.exists(filename):
                    if args.verbose: print('>> Creating directory %s' % (filename))
                    if not args.dry: sftp.mkdir(filename)
                with sftp.cd(filename):
                    if not sftp.exists(RESOURCES_DIR):
                        if args.verbose: print('>> Creating directory %s/%s' % (filename, RESOURCES_DIR))
                        if not args.dry: sftp.mkdir(RESOURCES_DIR)
                    if not args.skip_resources:
                        if args.verbose: print('>> Uploading resource files')
                        if not args.dry: sftp.put_d(l_rdir_path, RESOURCES_DIR, preserve_mtime=False)
                    if not args.skip_existing:
                        if args.verbose: print('>> Uploading XML file')
                        if not args.dry: sftp.put(l_xml_path, preserve_mtime=False)

parser = argparse.ArgumentParser(description='Manages transfering DDEX files to a remote location.')
parser.add_argument('host')
parser.add_argument('--username', default='', dest='user')
parser.add_argument('--password', default='')
parser.add_argument('dir')
parser.add_argument('-v', '--verbose', dest='verbose', action='store_true')
parser.add_argument('--update-timestamps', dest='update_timestamps', action='store_true', help='Indicates that previous timestamped files should be renamed.')
parser.add_argument('--target-dir', dest='target_dir', default='upload')
parser.add_argument('--skip-existing', dest='skip_existing', action='store_true')
parser.add_argument('--skip-resources', dest='skip_resources', action='store_true')
parser.add_argument('-d', '--dry', action='store_true')
args = parser.parse_args()
send_releases(args)
