import sys

from .console import console

console.quiet = False

def main():
    from .cli import CLI
    
    cli = CLI(sys.argv)
    cli.parse_args(sys.argv[1:])

if __name__ == "__main__":
    main()
