import click
from datetime import datetime
import os
import time
import shutil
import hashlib
from PIL import Image

from collections import defaultdict

import exifread


PICTURE_ROOT = '/Volumes/BigStorage/pictures'

PATH_CW = {
    '01': '1 Jan',
    '02': '2 Feb',
    '03': '3 Mar',
    '04': '4 Apr',
    '05': '5 May',
    '06': '6 Jun',
    '07': '7 Jul',
    '08': '8 Aug',
    '09': '9 Sep',
    '10': '10 Oct',
    '11': '11 Nov',
    '12': '12 Dec',
}


@click.group()
def cli():
    pass


def getCreationTime(fn):
    # return datetime.timetuple or None
    dt = None
    if '.jpeg' in fn:
        with open(fn, 'rb') as f:
            tags = exifread.process_file(f)
            taken = tags.get('EXIF DateTimeOriginal')
            if taken:
                dt = time.strptime(taken.values, '%Y:%m:%d %H:%M:%S')
    else:
        secs = os.path.getmtime(os.path.expanduser(fn))
        txt = time.ctime(secs)
        dt = datetime.strptime(txt, "%a %b %d %H:%M:%S %Y").timetuple()

    return dt


def getUniqueDestination(mvpath, fn, dt, originalFN=None):
    """
    Given a path, filename, and date-time,
    return a unique filename for this path, based on the date-time.
    """
    ext = os.path.splitext(fn)[1]
    newFnRoot = time.strftime('%Y-%m-%d %H.%M.%S', dt)

    # get unique filename
    dest = os.path.join(mvpath, newFnRoot + ext)

    # short-circuit if file is already named what it should be named
    if dest == originalFN:
        return dest

    if os.path.exists(dest):
        i = 1
        while True:
            newfn = u'{} ({}){}'.format(newFnRoot, i, ext)
            i += 1
            dest = os.path.join(mvpath, newfn)
            if not os.path.exists(dest):
                break

    return dest


@cli.command()
@click.argument('path', type=click.Path(exists=True))
def move_files(path):
    """
    Move files from input to archive

        - PATH: path to move files from
    """
    unmoved = 0
    for fn in os.listdir(path):
        full_fn = os.path.join(path, fn)
        dt = getCreationTime(full_fn)
        if dt:
            yr = str(dt.tm_year)
            mon = PATH_CW[str(dt.tm_mon).zfill(2)]

            # make path if it doesn't exist
            mvpath = os.path.join(PICTURE_ROOT, yr, mon)
            if not os.path.exists(mvpath):
                os.makedirs(mvpath)

            dest = getUniqueDestination(mvpath, fn, dt, originalFN=full_fn)
            print('{0}->{1}'.format(full_fn, dest))
            shutil.move(full_fn, dest)
        else:
            unmoved += 0

    print('{} files were not moved'.format(unmoved))


@cli.command()
@click.argument('root', type=click.Path(exists=True))
@click.option('--confirm', default=False, is_flag=True, help='Show files and confirm duplicate deletion')
def detect_dups(root, confirm=False):
    """
    Detect and remove duplicates in path

        - ROOT: path begin traversal of duplicate removal
    """

    paths = [p for p, _, _ in os.walk(root)]

    for path in paths:
        print('Traversing {}'.format(path))
        # get md5 hash for all files in path
        fns = [
            os.path.join(path, fn)
            for fn in os.listdir(path)
        ]
        tups = [
            (fname, hashlib.sha256(open(fname, 'rb').read()).digest())
            for fname in fns
            if os.path.isfile(fname)
        ]
        d = defaultdict(list)

        for tup in tups:
            d[tup[1]].append(tup[0])

        # find duplicate md5 hash
        dups = []
        for hash_, files in d.iteritems():
            if len(files) > 1:
                dups.append(files)

        # show dups using viewer
        for fns in dups:
            fns = sorted(set(fns))

            should_delete = True
            if confirm:
                for fn in fns:
                    print(fn)
                    try:
                        img = Image.open(fn)
                        img.show()
                    except IOError:
                        os.system('open "{}"'.format(fn))

                inp = raw_input("Delete one or more duplicates [y or n]? ")
                should_delete = inp.lower() == 'y'

            if should_delete:
                for fn in fns[1:]:
                    print("Deleting {}".format(fn))
                    os.remove(fn)


@cli.command()
@click.argument('root', type=click.Path(exists=True))
def rename_files(root):
    """
    Rename files using date-time information from file

        - ROOT: path begin traversal of duplicate removal
    """
    paths = [p for p, _, _ in os.walk(root)]
    for path in paths:
        print('Traversing {} files in {}'.format(len(os.listdir(path)), path))
        files = [fn for fn in os.listdir(path) if os.path.isfile(os.path.join(path, fn))]
        for fn in files:
            full_fn = os.path.join(path, fn)
            dt = getCreationTime(full_fn)
            if dt:
                dest = getUniqueDestination(path, fn, dt, originalFN=full_fn)
                if full_fn != dest:
                    os.rename(full_fn, dest)


if __name__ == '__main__':
    cli()
