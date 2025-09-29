import os
import sys
from pathlib import Path

from django.core.management import execute_from_command_line


def main():
    project_dir = Path(__file__).resolve().parent / "mysite"
    sys.path.insert(0, str(project_dir))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")

    argv = [sys.argv[0], "runserver", *sys.argv[1:]]
    execute_from_command_line(argv)


if __name__ == "__main__":
    main()
