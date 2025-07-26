import argparse
import logging
import sys

from colorama import Fore, Style

from tatami import __version__
from tatami.config import load_config
from tatami.convention import build_from_dir, create_project
from tatami.doctor import diagnose_project, MessageLevel


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

    doctor_parser = subparsers.add_parser('doctor', help='Get project diagnostics')
    doctor_parser.add_argument('project', action='store', help='Path to the project')

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

        print(f'{Fore.GREEN}{Style.BRIGHT}🌱 Tatami {__version__}{Style.RESET_ALL}')
        print(f'Running app {Fore.GREEN}{parsed_args.project}{Fore.RESET} on {Fore.GREEN}http://{parsed_args.host}:{parsed_args.port}{Fore.RESET}')
        print(f'{Fore.GREEN}{Style.BRIGHT}     • Config: {Style.RESET_ALL}{Fore.GREEN}{app.summary.config_file}')
        print(f'{Fore.GREEN}{Style.BRIGHT}     • Routers: {Style.RESET_ALL}{Fore.GREEN}{app.summary.routers} discovered')
        print(f'{Fore.GREEN}{Style.BRIGHT}     • Static files: {Style.RESET_ALL}{Fore.GREEN}{app.summary.static}')
        print(f'{Fore.GREEN}{Style.BRIGHT}     • Templates: {Style.RESET_ALL}{Fore.GREEN}{app.summary.templates}')
        print(f'{Fore.GREEN}{Style.BRIGHT}     • Middleware: {Style.RESET_ALL}{Fore.GREEN}{app.summary.middleware} loaded{Fore.RESET}')
        print(f'Run {Style.BRIGHT}tatami doctor "{parsed_args.project}"{Style.RESET_ALL} for a more detailed analysis 🩺')
        print('Handing control over to uvicorn...')
        # run the app
        app.run(host=parsed_args.host, port=parsed_args.port, server=parsed_args.server)

    elif parsed_args.action == 'doctor':
        print('🩺 Tatami is checking your project...')
        diagnose = diagnose_project(parsed_args.project)
        
        # Display messages by level
        success_count = 0
        for message in diagnose.detail:
            if message.level == MessageLevel.DEFAULT:
                print(f'✔ {message.message}')
                success_count += 1
            elif message.level == MessageLevel.WARNING:
                print(f'{Fore.YELLOW}⚠ {message.message}{Fore.RESET}')
            elif message.level == MessageLevel.LOW:
                print(f'{Fore.CYAN}ℹ {message.message}{Fore.RESET}')
            elif message.level == MessageLevel.MEDIUM:
                print(f'{Fore.YELLOW}! {message.message}{Fore.RESET}')
            elif message.level == MessageLevel.HIGH:
                print(f'{Fore.RED}!! {message.message}{Fore.RESET}')
            elif message.level == MessageLevel.CRITICAL:
                print(f'{Fore.RED}{Style.BRIGHT}!!! {message.message}{Style.RESET_ALL}')
        
        print()
        
        # Display summary
        summary = diagnose.summary
        if summary.critical > 0:
            print(f'{Fore.RED}{Style.BRIGHT}❌ Critical issues found! Your project may not work properly.{Style.RESET_ALL}')
        elif summary.high > 0 or summary.medium > 0:
            print(f'{Fore.YELLOW}⚠ Some issues found, but your project should work.{Style.RESET_ALL}')
        elif summary.warning > 0 or summary.low > 0:
            print(f'{Fore.GREEN}✅ Your project looks good! Minor suggestions available.{Style.RESET_ALL}')
        else:
            print(f'{Fore.GREEN}{Style.BRIGHT}✅ All systems look sharp, sensei! 🥋{Style.RESET_ALL}')

    else:
        parser.print_help()

if __name__ == '__main__':
    main()
