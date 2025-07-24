import argparse
import logging
import sys

from tatami.config import load_config
from tatami.convention import build_from_dir, create_project
from tatami.core import run


def main():
    parser = argparse.ArgumentParser(sys.argv[0])

    subparsers = parser.add_subparsers(dest='action', help='The action to perform')
    run_parser = subparsers.add_parser('run', help='Run an application')

    run_parser.add_argument('project', action='store', help='Project name. A valid system path name')
    run_parser.add_argument('--host', action='store', default='localhost', help='The host where the app will be running')
    run_parser.add_argument('--port', type=int, action='store', default='8000', help='The host where the app server will be listening')
    run_parser.add_argument('--mode', action='store', default=None, help='The config the app will be using. If not provided, the default config will be loaded')
    run_parser.add_argument('-v', '--verbose', action='count', default=0, help='How verbose should I be?')
    run_parser.add_argument('--server', action='store', default='uvicorn', choices=['uvicorn', 'gunicorn'], help='Which server backend should be used? Default is uvicorn')

    create_parser = subparsers.add_parser('create', help='Create a new project')
    create_parser.add_argument('project', action='store', help='Project name. A valid system path name')
    create_parser.add_argument('-t', '--template', action='store', default=None, help='Create the project using the provided template')

    parsed_args = parser.parse_args(sys.argv[1:])

    if parsed_args.action == 'create':
        if parsed_args.template is not None:
            raise NotImplementedError('Creating a project from a template is not implemented yet')
        
        create_project(parsed_args.project)

    elif parsed_args.action == 'run':
        if parsed_args.verbose > 0:
            logger = logging.getLogger('tatami')
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(logging.Formatter('%(name)s (%(levelname)s): %(message)s'))
            logger.addHandler(handler)

            if parsed_args.verbose == 1:
                logger.setLevel(logging.INFO)
        
            elif parsed_args.verbose == 2:
                logger.setLevel(logging.DEBUG)

        app = build_from_dir(parsed_args.project, parsed_args.mode)

        # run the app
        # TODO make uvicorn the default, add option to run using another backend and check import for gunicorn, tornado, etc.
        run(app, host=parsed_args.host, port=parsed_args.port)

    else:
        parser.print_help()

if __name__ == '__main__':
    main()
