import argparse
from fnmatch import fnmatch

from barber.utils import logger, config
from barber.app import collection
from barber.mc import MinioClient

cfg = config()


def upload(args):
    mc = MinioClient(cfg['destination']['host_alias'])
    for name, folders in collection.folders.items():
        if any(fnmatch(name, ptrn) for ptrn in args.patterns):
            logger.info("Upload folder %s", name)
            for folder in folders:
                folder.upload(mc)


def show_collection(args):
    for name, folders in collection.folders.items():
        print(name)
        for fld in folders:
            nb_img = len(fld.images)
            nb_starred = len([i for i in fld.images if i.starred])
            print(f'  {fld.path} ({nb_img} images, {nb_starred} starred)')


def run():
    # top-level parser
    parser = argparse.ArgumentParser(
        prog="barber",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--verbose", "-v", action="count", help="Increase verbosity", default=0
    )
    subparsers = parser.add_subparsers(dest="command")

    parser_upload = subparsers.add_parser("upload")
    parser_upload.add_argument("patterns", nargs="*")
    parser_upload.set_defaults(func=upload)

    parser_collection = subparsers.add_parser("collection")
    parser_collection.set_defaults(func=show_collection)

    # Parse args
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return
    # Adapt log level
    match args.verbose:
        case 1: logger.setLevel("INFO")
        case 2: logger.setLevel("DEBUG")
        case _: logger.setLevel("WARN")
    try:
        args.func(args)
    except (BrokenPipeError, KeyboardInterrupt):
        pass
