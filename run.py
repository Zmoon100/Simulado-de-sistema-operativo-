import argparse
from sim_os import OperatingSystem, CommandLineInterface


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    os_sim = OperatingSystem()
    cli = CommandLineInterface(os_sim)
    if args.demo:
        result = cli._demo_sequence([])
        if result is not None:
            cli._print(result)
        return
    cli.run()


if __name__ == "__main__":
    main()
